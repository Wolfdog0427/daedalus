# knowledge/adaptive_pacer.py

"""
Adaptive Pacer

Controls the speed and intensity of knowledge acquisition based on
real-time quality signals. Prevents the learning loop from outrunning
the system's ability to maintain coherence and consistency.

Mirrors the drift-aware parameter tuning in the SHO, applied to
knowledge acquisition rather than patch application.

Signals consumed:
- Graph coherence (from self-model)
- Consistency score (from self-model)
- Drift level (from drift detector)
- Recent batch quality deltas (from batch ingestion reports)

Outputs:
- Batch size recommendation
- Verification intensity recommendation
- Whether to pause, continue, or accelerate
- Cooldown period between batches
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from collections import deque

from knowledge.self_model import get_self_model

try:
    from knowledge.flow_tuner import flow_tuner as _flow_tuner
    _FLOW_TUNER_AVAILABLE = True
except ImportError:
    _FLOW_TUNER_AVAILABLE = False


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

DEFAULT_BATCH_SIZE = 10
MIN_BATCH_SIZE = 3
MAX_BATCH_SIZE = 50

DEFAULT_COOLDOWN_SEC = 2.0
MIN_COOLDOWN_SEC = 0.5
MAX_COOLDOWN_SEC = 30.0

COHERENCE_FLOOR = 0.25
CONSISTENCY_FLOOR = 0.30

CIRCUIT_BREAKER_OPEN_THRESHOLD = 0.40
CIRCUIT_BREAKER_CLOSE_THRESHOLD = 0.50
CIRCUIT_BREAKER_SUSTAINED_SEC = 60.0


# ------------------------------------------------------------
# LONG-TERM TREND TRACKER (F11)
# ------------------------------------------------------------

class LongTermTracker:
    """
    Rolling window for long-horizon trend detection.

    T5: Hysteresis — requires CONSECUTIVE_DECLINE_THRESHOLD consecutive
    declining readings before reporting trend as "declining". A single
    below-threshold reading no longer triggers deceleration.
    """

    CONSECUTIVE_DECLINE_THRESHOLD = 3

    def __init__(self, short_window: int = 100, long_window: int = 1000) -> None:
        self._short: deque = deque(maxlen=short_window)
        self._long: deque = deque(maxlen=long_window)
        self._consecutive_decline: int = 0
        self._consecutive_improve: int = 0

    def record(self, value: float) -> None:
        self._short.append(value)
        self._long.append(value)
        self._cached_trend = self._compute_trend()

    def short_mean(self) -> float:
        return sum(self._short) / len(self._short) if self._short else 0.0

    def long_mean(self) -> float:
        return sum(self._long) / len(self._long) if self._long else 0.0

    def _compute_trend(self) -> str:
        """Internal trend computation — mutates consecutive counters."""
        if len(self._long) < 20:
            return "insufficient_data"
        short_avg = self.short_mean()
        long_avg = self.long_mean()
        delta_pct = (short_avg - long_avg) / max(long_avg, 0.001)

        if delta_pct < -0.05:
            self._consecutive_decline += 1
            self._consecutive_improve = 0
        elif delta_pct > 0.05:
            self._consecutive_improve += 1
            self._consecutive_decline = 0
        else:
            self._consecutive_decline = 0
            self._consecutive_improve = 0

        if self._consecutive_decline >= self.CONSECUTIVE_DECLINE_THRESHOLD:
            return "declining"
        if self._consecutive_improve >= self.CONSECUTIVE_DECLINE_THRESHOLD:
            return "improving"
        return "stable"

    def trend(self) -> str:
        """Read-only access to cached trend (safe to call multiple times)."""
        return getattr(self, "_cached_trend", "insufficient_data")

    def count(self) -> int:
        return len(self._long)

    def summary(self) -> Dict[str, Any]:
        return {
            "short_mean": round(self.short_mean(), 4),
            "long_mean": round(self.long_mean(), 4),
            "trend": self.trend(),
            "samples": self.count(),
            "consecutive_decline": self._consecutive_decline,
        }


# ------------------------------------------------------------
# CONSISTENCY CIRCUIT BREAKER (F1)
# ------------------------------------------------------------

class ConsistencyCircuitBreaker:
    """
    Halts ingestion when consistency falls below a threshold.
    Only re-opens after sustained recovery above the close threshold.
    This prevents the ingestion rate from outrunning the repair loop.
    """

    def __init__(self) -> None:
        self.is_open: bool = False
        self.opened_at: float = 0.0
        self._close_candidate_since: float = 0.0
        self.open_count: int = 0
        self.last_consistency: float = 1.0

    def evaluate(self, consistency: float) -> bool:
        """Returns True if breaker is OPEN (ingestion should be blocked)."""
        self.last_consistency = consistency

        if not self.is_open:
            if consistency < CIRCUIT_BREAKER_OPEN_THRESHOLD:
                self.is_open = True
                self.opened_at = time.time()
                self._close_candidate_since = 0.0
                self.open_count += 1
        else:
            if consistency >= CIRCUIT_BREAKER_CLOSE_THRESHOLD:
                if self._close_candidate_since == 0.0:
                    self._close_candidate_since = time.time()
                elif time.time() - self._close_candidate_since >= CIRCUIT_BREAKER_SUSTAINED_SEC:
                    self.is_open = False
                    self._close_candidate_since = 0.0
            else:
                self._close_candidate_since = 0.0

        return self.is_open

    def status(self) -> Dict[str, Any]:
        return {
            "is_open": self.is_open,
            "open_count": self.open_count,
            "last_consistency": self.last_consistency,
            "opened_at": self.opened_at if self.is_open else None,
        }


# ------------------------------------------------------------
# GLOBAL TRACKERS
# ------------------------------------------------------------

_circuit_breaker = ConsistencyCircuitBreaker()
_coherence_tracker = LongTermTracker()
_consistency_tracker = LongTermTracker()
_quality_tracker = LongTermTracker()


def get_circuit_breaker() -> ConsistencyCircuitBreaker:
    return _circuit_breaker


def get_long_term_trends() -> Dict[str, Any]:
    return {
        "coherence": _coherence_tracker.summary(),
        "consistency": _consistency_tracker.summary(),
        "quality": _quality_tracker.summary(),
        "circuit_breaker": _circuit_breaker.status(),
    }


# ------------------------------------------------------------
# PACE STATE
# ------------------------------------------------------------

class PaceState:
    """Tracks recent acquisition quality for adaptive decisions."""

    def __init__(self) -> None:
        self.recent_deltas: List[Dict[str, float]] = []
        self.consecutive_degradations: int = 0
        self.consecutive_improvements: int = 0
        self.last_batch_time: float = 0.0
        self.current_batch_size: int = DEFAULT_BATCH_SIZE
        self.current_cooldown: float = DEFAULT_COOLDOWN_SEC

    def record_batch(self, quality_before: Dict[str, Any], quality_after: Dict[str, Any]) -> None:
        coherence_delta = (
            quality_after.get("coherence", 0) - quality_before.get("coherence", 0)
        )
        consistency_delta = (
            quality_after.get("consistency", 0) - quality_before.get("consistency", 0)
        )

        self.recent_deltas.append({
            "coherence": coherence_delta,
            "consistency": consistency_delta,
            "timestamp": time.time(),
        })

        self.recent_deltas = self.recent_deltas[-20:]

        if coherence_delta < -0.02 or consistency_delta < -0.02:
            self.consecutive_degradations += 1
            self.consecutive_improvements = 0
        elif coherence_delta > 0.01 or consistency_delta > 0.01:
            self.consecutive_improvements += 1
            self.consecutive_degradations = 0
        else:
            pass

        # Feed long-term trackers
        _coherence_tracker.record(quality_after.get("coherence", 0))
        _consistency_tracker.record(quality_after.get("consistency", 0))
        _quality_tracker.record(quality_after.get("quality", 0))

        # Feed circuit breaker
        _circuit_breaker.evaluate(quality_after.get("consistency", 0))

        self.last_batch_time = time.time()


_pace_state = PaceState()


def get_pace_state() -> PaceState:
    return _pace_state


# ------------------------------------------------------------
# PACE COMPUTATION
# ------------------------------------------------------------

def compute_pace() -> Dict[str, Any]:
    """
    Compute the recommended acquisition pace based on current
    system health, recent history, AND long-term trends.
    """
    sm = get_self_model()
    coherence = sm["confidence"]["graph_coherence"]
    consistency = sm["confidence"]["consistency"]
    state = _pace_state

    # --- Circuit breaker: absolute halt ---
    _circuit_breaker.evaluate(consistency)
    if _circuit_breaker.is_open:
        return _pause("circuit_breaker_open", state)

    # Hard floor: pause if quality is critically low
    if coherence < COHERENCE_FLOOR:
        return _pause("coherence_critically_low", state)

    if consistency < CONSISTENCY_FLOOR:
        return _pause("consistency_critically_low", state)

    # Consecutive degradations: decelerate or pause
    if state.consecutive_degradations >= 3:
        return _pause("three_consecutive_degradations", state)

    if state.consecutive_degradations >= 2:
        return _decelerate("two_consecutive_degradations", state)

    # Long-term trend detection (F11): if short-term is declining
    # relative to long-term, decelerate even if recent batches look OK
    consistency_trend = _consistency_tracker.trend()
    coherence_trend = _coherence_tracker.trend()
    if consistency_trend == "declining" or coherence_trend == "declining":
        return _decelerate("long_term_trend_declining", state)

    # Consecutive improvements: accelerate only if long-term is also stable/improving
    if state.consecutive_improvements >= 3 and coherence > 0.6 and consistency > 0.6:
        if consistency_trend != "declining" and coherence_trend != "declining":
            return _accelerate("stable_improvement_streak", state)

    # Consult flow tuner for batch size optimization
    if _FLOW_TUNER_AVAILABLE:
        recommended = _flow_tuner.get_recommended_batch_size()
        if MIN_BATCH_SIZE <= recommended <= MAX_BATCH_SIZE:
            state.current_batch_size = recommended

    return _continue(state)


def _pause(reason: str, state: PaceState) -> Dict[str, Any]:
    state.current_batch_size = MIN_BATCH_SIZE
    state.current_cooldown = MAX_COOLDOWN_SEC
    return {
        "action": "pause",
        "batch_size": MIN_BATCH_SIZE,
        "verification_intensity": "deep",
        "cooldown_sec": MAX_COOLDOWN_SEC,
        "reason": reason,
    }


def _decelerate(reason: str, state: PaceState) -> Dict[str, Any]:
    new_size = max(MIN_BATCH_SIZE, state.current_batch_size // 2)
    new_cooldown = min(MAX_COOLDOWN_SEC, state.current_cooldown * 1.5)
    state.current_batch_size = new_size
    state.current_cooldown = new_cooldown
    return {
        "action": "decelerate",
        "batch_size": new_size,
        "verification_intensity": "standard",
        "cooldown_sec": new_cooldown,
        "reason": reason,
    }


def _accelerate(reason: str, state: PaceState) -> Dict[str, Any]:
    new_size = min(MAX_BATCH_SIZE, int(state.current_batch_size * 1.5))
    new_cooldown = max(MIN_COOLDOWN_SEC, state.current_cooldown * 0.7)
    state.current_batch_size = new_size
    state.current_cooldown = new_cooldown
    return {
        "action": "accelerate",
        "batch_size": new_size,
        "verification_intensity": "light",
        "cooldown_sec": new_cooldown,
        "reason": reason,
    }


def _continue(state: PaceState) -> Dict[str, Any]:
    return {
        "action": "continue",
        "batch_size": state.current_batch_size,
        "verification_intensity": "standard",
        "cooldown_sec": state.current_cooldown,
        "reason": "nominal",
    }


# ------------------------------------------------------------
# INTEGRATION HELPERS
# ------------------------------------------------------------

def should_acquire_now() -> bool:
    """Check if enough time has elapsed since the last batch."""
    state = _pace_state
    if state.last_batch_time == 0:
        return True
    elapsed = time.time() - state.last_batch_time
    return elapsed >= state.current_cooldown


def record_batch_result(
    quality_before: Dict[str, Any],
    quality_after: Dict[str, Any],
) -> None:
    """Record a batch result for adaptive pacing."""
    _pace_state.record_batch(quality_before, quality_after)


def reset_pace() -> None:
    """Reset pace state (for testing or operator override)."""
    global _pace_state
    _pace_state = PaceState()
