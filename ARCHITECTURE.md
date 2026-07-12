# Nirnay-112 — Architecture

Real-time emergency-call triage for Hindi/Hinglish 112 calls. The defining design
choice is a **split between perception and decisioning**: a large language model is
used only to *perceive* (transcribe speech, extract candidate signals), while every
*decision* that affects a caller — urgency, escalation, what to ask next — is made by
a **deterministic, explainable, auditable** engine that never calls an LLM.

This document describes the system as built. Module paths are given so each claim is
traceable to code.

---

## 1. Why this split

Emergency dispatch is safety-critical. LLM outputs are non-deterministic and can
hallucinate, so letting a model decide escalation is unacceptable: the same call could
yield different actions on reruns, and a wrong "calm" label could gate a caller away
from help. Nirnay therefore constrains the LLM to the perception boundary and makes the
decision layer a pure function of observable signals.

| Concern | Owner | Property |
|---|---|---|
| Speech-to-text, entity extraction | OpenAI (perception) | best-effort, tolerated to be noisy |
| Urgency, escalation, next question, memory | Deterministic engine | reproducible, explainable, testable |

---

## 2. Data flow

```
Browser (React + Web Audio)
  │  audio chunks over WebSocket
  ▼
FastAPI WebSocket  (app/websocket.py, /ws/call)
  ├─ STT ....................... app/speech/openai_stt.py        [LLM]
  ├─ Signal extraction ......... app/nlp/signal_extraction.py    [LLM + rules]
  ├─ Context update + guard .... app/logic/context_memory.py     [deterministic]
  ├─ Stress scoring ............ app/ml/stress_estimator.py      [deterministic]
  ├─ Urgency scoring ........... app/logic/urgency_scoring.py    [deterministic]
  ├─ Escalation rules .......... app/logic/escalation.py         [deterministic]
  ├─ Explainability ............ app/logic/explainability.py     [deterministic]
  └─ Audit log ................. app/logic/event_log.py          [append-only]
```

Everything below the STT/extraction line is deterministic and unit-tested.

---

## 3. Three-layer information model

`ContextMemory` (`app/logic/context_memory.py`) is the per-session state object:

- **Layer 1 — Critical:** `incident_type`, `location`, derived `urgency`. Missing Layer-1
  fields are an escalation trigger.
- **Layer 2 — Operational:** `caller_name`, `people_affected`, `immediate_danger`, etc.
- **Layer 3 — ML signals (never asked directly):** emotion history, clarity, language,
  repetition.

Each field carries a **confidence**, a **source**, and a **timestamp**.

---

## 4. The safety layer: confidence gating + rollback

`update_from_signals()` is the heart of the "don't let a misperception lock in" design:

1. **Snapshot first.** A `ContextSnapshot` of current state is taken before any change,
   so any update is reversible (`create_snapshot()` / `rollback_to_snapshot()`).
2. **Rollback guards** (`_should_rollback`) reject an update when:
   - an extracted entity **contradicts** an established one (e.g. location "Mumbai" then
     "Delhi" with no overlap), or
   - transcription **clarity < 0.3**, or
   - a **hallucination flag** was raised earlier in the session.
   On a contradiction the hallucination flag is set, making the session conservative
   thereafter.
3. **Confidence-gated writes.** A field is overwritten only if the *new* confidence
   exceeds the *decayed* existing confidence. Confidence **decays linearly over time**
   (`_apply_confidence_decay`), so an early high-confidence mistake loses ground and a
   later correct value can win — preventing permanent lock-in.

## 5. Deterministic scoring

**Stress** (`app/ml/stress_estimator.py`) — a weighted blend of observable signals, no
emotion LLM: panic-keyword frequency (Hindi + English, 0.35), repetition (0.25),
speaking rate in words/sec (0.25), exclamation usage (0.15). Fully explainable: every
score traces to the keywords found, the rate, and the counts.

**Urgency** (`app/logic/urgency_scoring.py`) — an explicit weighted sum:

```
urgency = 0.50·intent + 0.25·stress + 0.15·repetition
        + 0.05·(1 − clarity) + 0.05·time_pressure + 0.10·urgency_signals
```

mapped to `critical / high / medium / low` by fixed thresholds. Intent weights are a
documented table (fire 0.95, medical 0.90, …); a special case keeps dog-bites below the
critical threshold.

**Escalation** (`app/logic/escalation.py`) — any one rule forces a human: urgency over
threshold, clarity too low, panic persisting across turns, critical fields still missing
after N questions, an immediate-danger flag, or an explicit request for a human.

## 6. Explainability & audit

`explain_decision()` emits, for every decision, the urgency level, the top-3
contributing factors in human language, the escalation reason, and confidence warnings —
with **no LLM and no change to the decision logic**. `event_log.py` keeps a per-session,
append-only trail (`transcription_received`, `context_updated`, `escalation_triggered`,
`rollback_occurred`, `api_failure`), surfaced at `GET /admin/session/{id}/events`.

---

## 7. Testing & CI

The deterministic core is covered by a **43-test** suite (`backend/tests/`) that runs
with **only the standard library + pytest** — no OpenAI, no network — so it is fast
(~0.1s) and hermetic. It pins: stress-signal behavior, the urgency formula and its
thresholds (including the dog-bite case), every escalation rule, the
snapshot/rollback and confidence-gating guarantees, explanation structure, and the
append-only audit log. GitHub Actions runs it on every push and PR
(`.github/workflows/ci.yml`).

```bash
cd backend
pip install pytest
python -m pytest tests -q
```

---

## 8. Honest limitations

- The intent classifier (TF-IDF + Logistic Regression, `app/ml/`) is a small local model
  trained on a modest dataset; it is a baseline, not a production ASR-robust NLU.
- The audit log is in-memory (per process), suitable for a demo/dispatcher console, not
  yet a durable store.
- Perception quality is bounded by STT accuracy on noisy, code-switched audio; the
  deterministic layer is designed to *contain* that uncertainty, not remove it.
