
**Nirnay-112** — real-time emergency call triage for Hindi/Hinglish using a **hybrid pipeline**: OpenAI for speech/perception + **deterministic local decision logic** + auditability.

---

## Problem Statement / Motivation

Emergency calls in India are frequently **noisy**, **code-switched (Hindi/English)**, and **information-incomplete** (caller may not know exact address / incident type). Dispatchers need a system that:

- Streams transcripts and extracted incident details **during the call** (not post-call).
- Avoids black-box decisions in a safety-critical workflow (**urgency/escalation must be explainable**).
- Handles messy inputs: **broken sentences, repetition, panic language**, and partial locations.

---

## Features & Key Highlights

- **Real-time WebSocket pipeline** (`/ws/call`): audio chunks → STT → triage → UI updates.
- **Deterministic urgency scoring** (`backend/app/logic/urgency_scoring.py`): explicit weighted formula combining intent-weight, stress, repetition, clarity, and time pressure.
- **Rule-based stress estimation** (`backend/app/ml/stress_estimator.py`): repetition + panic-keywords (Hindi/English) + speaking-rate proxy + exclamation usage → \(0..1\) stress score.
- **Context Memory with safety controls** (`backend/app/logic/context_memory.py`):
  - confidence-based updates (no “first update wins”)
  - linear confidence decay (prevents hallucination lock-in)
  - snapshot + rollback on contradiction / low clarity / hallucination flag
- **Decision explainability** (`backend/app/logic/explainability.py`): JSON explanation with top contributing factors + confidence warnings (no ML / no OpenAI).
- **Append-only audit log (in-memory)** (`backend/app/logic/event_log.py`) + debug endpoint:
  - `GET /admin/session/{session_id}/events`
- **Local intent classifier (TF‑IDF + Logistic Regression)** (`backend/app/ml/intent_classifier.py`) + training script (`backend/app/ml/train_intent.py`) and dataset (`backend/app/ml/data/intent_dataset.csv`).
- **Offline evaluation harness** (`evaluation/`): deterministic evaluation without OpenAI calls.
- **Dispatcher-style frontend (light theme)** (`frontend/nirnay-ui/`): multi-panel console (transcript, incident details, escalation/explainability, system status).

---

## Technologies & Tools

### Backend
- **Python** + **FastAPI** + **Uvicorn**: async WebSocket + REST endpoints.
- **OpenAI Python SDK**: speech-to-text + perception-layer signal extraction.
- **Pydantic**: schema validation / structured responses.
- **NumPy**: audio utilities.
- **scikit-learn** *(recommended)*: TF‑IDF + Logistic Regression for local intent classification.

### Frontend
- **React + Vite**
- **Web Audio API**: mic capture + chunk streaming
- **WebSocket API**

### Evaluation
- Deterministic evaluation scripts in `evaluation/` (no OpenAI).

---

## Technical Challenges & Solutions

- **Safety-critical decisioning**
  - **Challenge**: LLM outputs are non-deterministic and can hallucinate.
  - **Solution**: keep escalation/urgency deterministic; use OpenAI only for perception signals and transcription.

- **Hallucination lock-in across turns**
  - **Challenge**: wrong early extraction can “stick” and block future corrections.
  - **Solution**: confidence-based updates + confidence decay + snapshot/rollback on contradiction/low-clarity.

- **Stress estimation without ML**
  - **Challenge**: emotion labels from LLMs are unstable.
  - **Solution**: deterministic stress score from observable transcript features.

- **Interface contract drift**
  - **Challenge**: STT may return structured dict while older code expects a string.
  - **Solution**: WebSocket handler supports both formats while preserving existing behavior.

---

## Architecture / Project Structure

### High-level architecture

```
Browser (React + WebAudio)
  └─ WebSocket audio chunks
      └─ FastAPI WebSocket (/ws/call)
          ├─ STT: backend/app/speech/openai_stt.py
          ├─ Signal extraction: backend/app/nlp/signal_extraction.py
          ├─ Context memory + rollback: backend/app/logic/context_memory.py
          ├─ Stress scoring: backend/app/ml/stress_estimator.py
          ├─ Urgency scoring: backend/app/logic/urgency_scoring.py
          ├─ Escalation rules: backend/app/logic/escalation.py
          ├─ Explainability: backend/app/logic/explainability.py
          └─ Audit log: backend/app/logic/event_log.py (+ admin endpoint)
```

### Repository map (relevant)

- **`backend/app/`**: FastAPI app + triage pipeline
  - `main.py`: app entrypoint
  - `websocket.py`: session + streaming pipeline
  - `logic/`: deterministic decision engine (context, urgency, escalation, explainability, audit log)
  - `nlp/`: signal extraction + India-specific keyword utilities
  - `speech/`: STT + TTS
  - `ml/`: local intent classifier + stress estimator + training assets
- **`frontend/nirnay-ui/`**: dispatcher console

---

## Installation & Setup

### Prerequisites
- Python 3.10+ recommended
- Node.js 18+
- OpenAI API key for live mode: `OPENAI_API_KEY`

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY="..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Optional helper:

```bash
./restart-backend.sh
```

### Frontend

```bash
cd frontend/nirnay-ui
npm install
npm run dev
```

Open: `http://localhost:5173`

---

## Usage / Demo

- Start backend + frontend.
- Allow microphone access in the browser.
- Begin call → speak short/noisy Hinglish phrases.
- Watch panels update:
  - transcript stream
  - incident fields + confidence/clarity
  - urgency + escalation decision
  - deterministic explanation (`decision_explanation`)

### Useful endpoints
- `GET /health`
- `GET /admin/session/{session_id}/events` (demo/debug audit trail)
- WebSocket: `ws://localhost:8000/ws/call`

---

## What this project demonstrates:

- **System design**: separation of perception vs decisioning; WebSocket session pipeline; audit logging.
- **Deterministic decision engine**: explicit scoring + thresholds + explainability output (testable/reviewable).
- **Robust state management**: confidence decay, snapshot/rollback, contradiction handling.
- **Applied ML fundamentals**: TF‑IDF + Logistic Regression classifier; reproducible training script; model persistence.
- **Evaluation mindset**: offline evaluation harness with measurable metrics + stated limitations.
- **Engineering hygiene**: clear module boundaries (`speech/`, `nlp/`, `logic/`, `ml/`), typed schemas, explicit failure handling.


---

## Contributing Guidelines

- **Branching**: feature branches from `main`
- **PRs**: include a short “why” + eval output (e.g., `python evaluation/evaluate.py`)
- **Guardrail**: keep escalation/urgency deterministic; avoid LLMs for decisions

---

- **Author**: Shaswat Naman (VIT Vellore, Batch 2028)


