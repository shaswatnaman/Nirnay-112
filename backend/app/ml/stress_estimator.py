"""
Deterministic Stress Estimator

This module provides rule-based stress scoring using multiple signals:
- Speech repetition count
- Panic keyword frequency (Hindi + English)
- Speaking rate proxy (word count / time)
- Exclamation usage

This is a deterministic, rule-based system - NO OpenAI or ML models.
All scoring is based on explicit rules and patterns.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Panic keywords in Hindi (with common variations)
HINDI_PANIC_KEYWORDS = [
    # Direct panic words
    "बचाओ", "मदद", "जल्दी", "तुरंत", "अभी", "हैल्प", "हेल्प",
    # Fear/panic expressions
    "डर", "भय", "घबराहट", "चिंता", "फिक्र", "परेशानी",
    # Urgency words
    "जरूरी", "अत्यंत", "बहुत", "बहुत जरूरी", "तत्काल",
    # Distress words
    "दुख", "पीड़ा", "तकलीफ", "मुसीबत", "संकट",
    # Emergency words
    "इमरजेंसी", "आपातकाल", "संकट", "मुसीबत",
    # Common exclamations
    "अरे", "ओह", "हाय", "अरे बाप रे", "हे भगवान"
]

# Panic keywords in English
ENGLISH_PANIC_KEYWORDS = [
    # Direct panic words
    "help", "save", "quick", "urgent", "emergency", "now", "immediately",
    # Fear/panic expressions
    "scared", "afraid", "fear", "panic", "worried", "anxious", "distressed",
    # Urgency words
    "urgent", "critical", "important", "asap", "right now",
    # Distress words
    "pain", "hurt", "injured", "bleeding", "trapped", "stuck",
    # Emergency words
    "emergency", "crisis", "danger", "dangerous", "unsafe",
    # Common exclamations
    "oh", "oh no", "oh god", "please", "god", "jesus"
]

# Combined panic keywords (case-insensitive matching)
ALL_PANIC_KEYWORDS = HINDI_PANIC_KEYWORDS + ENGLISH_PANIC_KEYWORDS


class StressEstimator:
    """
    Deterministic stress estimator using rule-based scoring.
    
    Calculates stress score (0.0 to 1.0) based on multiple signals:
    - Repetition count
    - Panic keyword frequency
    - Speaking rate (words per second)
    - Exclamation usage
    """
    
    def __init__(self):
        """Initialize the stress estimator."""
        pass
    
    def calculate_stress_score(
        self,
        transcript: str,
        repetition_count: int = 0,
        time_elapsed_seconds: Optional[float] = None,
        previous_transcripts: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Calculate stress score from transcript and context.
        
        Args:
            transcript: Current transcript text
            repetition_count: Number of times user has repeated similar content
            time_elapsed_seconds: Time elapsed since conversation started (for speaking rate)
            previous_transcripts: List of previous transcripts (for repetition detection)
        
        Returns:
            dict: Stress analysis with keys:
                - "stress_score": float - Overall stress score (0.0 to 1.0)
                - "components": dict - Individual component scores:
                    - "repetition_score": float
                    - "panic_keyword_score": float
                    - "speaking_rate_score": float
                    - "exclamation_score": float
                - "details": dict - Detailed breakdown:
                    - "panic_keywords_found": List[str]
                    - "panic_keyword_count": int
                    - "exclamation_count": int
                    - "word_count": int
                    - "speaking_rate": float (words per second, if time available)
        """
        if not transcript or not transcript.strip():
            return {
                "stress_score": 0.0,
                "components": {
                    "repetition_score": 0.0,
                    "panic_keyword_score": 0.0,
                    "speaking_rate_score": 0.0,
                    "exclamation_score": 0.0
                },
                "details": {
                    "panic_keywords_found": [],
                    "panic_keyword_count": 0,
                    "exclamation_count": 0,
                    "word_count": 0,
                    "speaking_rate": 0.0
                }
            }
        
        # Component 1: Repetition score (0.0 to 1.0)
        # Higher repetition indicates stress/panic
        repetition_score = self._calculate_repetition_score(repetition_count, previous_transcripts, transcript)
        
        # Component 2: Panic keyword frequency (0.0 to 1.0)
        panic_keyword_score, panic_keywords_found, panic_keyword_count = self._calculate_panic_keyword_score(transcript)
        
        # Component 3: Speaking rate (0.0 to 1.0)
        # Fast speaking indicates stress
        speaking_rate_score, word_count, speaking_rate = self._calculate_speaking_rate_score(
            transcript, time_elapsed_seconds
        )
        
        # Component 4: Exclamation usage (0.0 to 1.0)
        exclamation_score, exclamation_count = self._calculate_exclamation_score(transcript)
        
        # Combine components with weighted average
        # Weights can be adjusted based on which signals are most reliable
        weights = {
            "repetition": 0.25,
            "panic_keywords": 0.35,  # Most reliable indicator
            "speaking_rate": 0.25,
            "exclamation": 0.15
        }
        
        stress_score = (
            weights["repetition"] * repetition_score +
            weights["panic_keywords"] * panic_keyword_score +
            weights["speaking_rate"] * speaking_rate_score +
            weights["exclamation"] * exclamation_score
        )
        
        # Clamp to [0.0, 1.0]
        stress_score = max(0.0, min(1.0, stress_score))
        
        return {
            "stress_score": stress_score,
            "components": {
                "repetition_score": repetition_score,
                "panic_keyword_score": panic_keyword_score,
                "speaking_rate_score": speaking_rate_score,
                "exclamation_score": exclamation_score
            },
            "details": {
                "panic_keywords_found": panic_keywords_found,
                "panic_keyword_count": panic_keyword_count,
                "exclamation_count": exclamation_count,
                "word_count": word_count,
                "speaking_rate": speaking_rate
            }
        }
    
    def _calculate_repetition_score(
        self,
        repetition_count: int,
        previous_transcripts: Optional[List[str]],
        current_transcript: str
    ) -> float:
        """
        Calculate stress score from repetition.
        
        Args:
            repetition_count: Number of times user has repeated content
            previous_transcripts: List of previous transcripts
            current_transcript: Current transcript
        
        Returns:
            float: Repetition score (0.0 to 1.0)
        """
        score = 0.0
        
        # Base score from repetition count
        # 0 repetitions = 0.0, 3+ repetitions = 1.0 (sigmoid-like curve)
        if repetition_count > 0:
            score = min(1.0, repetition_count / 3.0)
        
        # Additional score if current transcript is similar to previous ones
        if previous_transcripts and len(previous_transcripts) > 0:
            # Check if current transcript is very similar to any previous transcript
            current_lower = current_transcript.lower().strip()
            for prev in previous_transcripts[-3:]:  # Check last 3 transcripts
                prev_lower = prev.lower().strip()
                # Simple similarity: if transcripts are very similar (80%+ overlap)
                if len(current_lower) > 0 and len(prev_lower) > 0:
                    # Calculate simple word overlap
                    current_words = set(current_lower.split())
                    prev_words = set(prev_lower.split())
                    if len(current_words) > 0 and len(prev_words) > 0:
                        overlap = len(current_words & prev_words) / max(len(current_words), len(prev_words))
                        if overlap > 0.7:  # 70% word overlap = high similarity
                            score = max(score, 0.7)
                            break
        
        return min(1.0, score)
    
    def _calculate_panic_keyword_score(self, transcript: str) -> Tuple[float, List[str], int]:
        """
        Calculate stress score from panic keyword frequency.
        
        Args:
            transcript: Text to analyze
        
        Returns:
            tuple: (score, keywords_found, keyword_count)
                - score: float (0.0 to 1.0)
                - keywords_found: List of panic keywords found
                - keyword_count: Total count of panic keywords
        """
        transcript_lower = transcript.lower()
        keywords_found = []
        
        # Find all panic keywords in transcript
        for keyword in ALL_PANIC_KEYWORDS:
            keyword_lower = keyword.lower()
            # Count occurrences (case-insensitive)
            count = transcript_lower.count(keyword_lower)
            if count > 0:
                keywords_found.extend([keyword] * count)
        
        keyword_count = len(keywords_found)
        
        # Calculate score based on keyword density
        # Normalize by word count to get frequency
        words = transcript.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.0, [], 0
        
        # Keyword frequency (keywords per 10 words)
        keyword_frequency = (keyword_count / word_count) * 10.0
        
        # Score: 0 keywords = 0.0, 1+ keywords per 10 words = 1.0
        # Use sigmoid-like curve: frequency / (frequency + 1)
        score = min(1.0, keyword_frequency / (keyword_frequency + 1.0))
        
        # Boost score if multiple keywords found
        if keyword_count >= 3:
            score = min(1.0, score * 1.2)
        
        return score, keywords_found, keyword_count
    
    def _calculate_speaking_rate_score(
        self,
        transcript: str,
        time_elapsed_seconds: Optional[float]
    ) -> Tuple[float, int, float]:
        """
        Calculate stress score from speaking rate (words per second).
        
        Fast speaking indicates stress/panic.
        
        Args:
            transcript: Text to analyze
            time_elapsed_seconds: Time elapsed since conversation started
        
        Returns:
            tuple: (score, word_count, speaking_rate)
                - score: float (0.0 to 1.0)
                - word_count: Number of words in transcript
                - speaking_rate: Words per second (0.0 if time not available)
        """
        words = transcript.split()
        word_count = len(words)
        
        if time_elapsed_seconds is None or time_elapsed_seconds <= 0:
            # Cannot calculate speaking rate without time
            # Use word count as proxy: very long transcripts might indicate stress
            # But this is less reliable, so give lower score
            if word_count > 50:  # Very long transcript
                return 0.3, word_count, 0.0
            return 0.0, word_count, 0.0
        
        # Calculate speaking rate (words per second)
        speaking_rate = word_count / time_elapsed_seconds
        
        # Normal speaking rate: ~2-3 words per second
        # Stressed speaking: 4+ words per second
        # Very stressed: 5+ words per second
        
        # Score based on speaking rate
        # 0-2 wps = 0.0 (normal)
        # 2-3 wps = 0.3 (slightly fast)
        # 3-4 wps = 0.6 (fast)
        # 4-5 wps = 0.8 (very fast)
        # 5+ wps = 1.0 (extremely fast)
        
        if speaking_rate <= 2.0:
            score = 0.0
        elif speaking_rate <= 3.0:
            score = 0.3
        elif speaking_rate <= 4.0:
            score = 0.6
        elif speaking_rate <= 5.0:
            score = 0.8
        else:
            score = 1.0
        
        return score, word_count, speaking_rate
    
    def _calculate_exclamation_score(self, transcript: str) -> Tuple[float, int]:
        """
        Calculate stress score from exclamation usage.
        
        High exclamation usage indicates stress/urgency.
        
        Args:
            transcript: Text to analyze
        
        Returns:
            tuple: (score, exclamation_count)
                - score: float (0.0 to 1.0)
                - exclamation_count: Number of exclamation marks found
        """
        # Count exclamation marks
        exclamation_count = transcript.count('!')
        
        # Also count Hindi exclamation equivalents (common in Hindi text)
        # Hindi often uses "!" but also has other patterns
        hindi_exclamations = ['अरे', 'ओह', 'हाय', 'अरे बाप रे']
        for exclamation in hindi_exclamations:
            exclamation_count += transcript.count(exclamation)
        
        # Normalize by word count
        words = transcript.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.0, 0
        
        # Exclamation frequency (exclamations per 10 words)
        exclamation_frequency = (exclamation_count / word_count) * 10.0
        
        # Score: 0 exclamations = 0.0, 1+ per 10 words = 1.0
        # Use sigmoid-like curve
        score = min(1.0, exclamation_frequency / (exclamation_frequency + 1.0))
        
        # Boost score if multiple exclamations
        if exclamation_count >= 3:
            score = min(1.0, score * 1.2)
        
        return score, exclamation_count


# Convenience function for easy usage
def estimate_stress(
    transcript: str,
    repetition_count: int = 0,
    time_elapsed_seconds: Optional[float] = None,
    previous_transcripts: Optional[List[str]] = None
) -> Dict[str, any]:
    """
    Estimate stress score from transcript and context.
    
    Convenience function that creates a StressEstimator and calculates stress.
    
    Args:
        transcript: Current transcript text
        repetition_count: Number of times user has repeated similar content
        time_elapsed_seconds: Time elapsed since conversation started
        previous_transcripts: List of previous transcripts
    
    Returns:
        dict: Stress analysis (see StressEstimator.calculate_stress_score)
    """
    estimator = StressEstimator()
    return estimator.calculate_stress_score(
        transcript=transcript,
        repetition_count=repetition_count,
        time_elapsed_seconds=time_elapsed_seconds,
        previous_transcripts=previous_transcripts
    )

