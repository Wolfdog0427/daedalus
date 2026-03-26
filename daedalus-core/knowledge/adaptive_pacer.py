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

        # Keep only recent history
        self.recent_deltas = self.recent_deltas[-20:]

        if coherence_delta < -0.02 or consistency_delta < -0.02:
            self.consecutive_degradations += 1
            self.consecutive_improvements = 0
        elif coherence_delta > 0.01 or consistency_delta > 0.01:
            self.consecutive_improvements += 1
            self.consecutive_degradations = 0
        else:
            pass  # neutral: don't reset either counter

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
    system health and recent acquisition history.

    Returns:
        {
            "action": "continue" | "accelerate" | "decelerate" | "pause",
            "batch_size": int,
            "verification_intensity": "light" | "standard" | "deep",
            "cooldown_sec": float,
            "reason": str,
        }
    """
    sm = get_self_model()
    coherence = sm["confidence"]["graph_coherence"]
    consistency = sm["confidence"]["consistency"]
    state = _pace_state

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

    # Consecutive improvements: accelerate
    if state.consecutive_improvements >= 3 and coherence > 0.6 and consistency > 0.6:
        return _accelerate("stable_improvement_streak", state)

    # Consult flow tuner for batch size optimization
    if _FLOW_TUNER_AVAILABLE:
        recommended = _flow_tuner.get_recommended_batch_size()
        if MIN_BATCH_SIZE <= recommended <= MAX_BATCH_SIZE:
            state.current_batch_size = recommended

    # Default: continue at current pace
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
