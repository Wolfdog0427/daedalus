# knowledge/adaptive_cadence.py

"""
Adaptive Cadence Manager

Dynamically adjusts meta-cognition tick rates based on system state.
Instead of a fixed 15-minute interval for all subsystems, cadence is
tiered and context-sensitive:

  Critical (verification, contamination defense): 3-5 min during load
  Maintenance (staleness, anti-entropy, compaction): 15-30 min
  Strategic (curiosity, goal planning, memory): 30-60 min
  ABP Mode: all tiers at 3-5 min during bootstrap
  Attack Mode: critical at 1-2 min until threat contained

The cadence manager does not run its own timer — it provides recommended
intervals that the Meta Reasoner consults each cycle.

Integration:
  meta_reasoner.py calls should_run_tier() each cycle to decide which
  subsystems to activate. The ABP sets a global multiplier that
  accelerates all tiers proportionally.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CadenceTier(str, Enum):
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"
    STRATEGIC = "strategic"


class CadenceMode(str, Enum):
    NORMAL = "normal"
    ABP_BOOTSTRAP = "abp_bootstrap"
    ATTACK_RESPONSE = "attack_response"
    IDLE = "idle"


@dataclass
class TierConfig:
    base_interval_sec: float
    min_interval_sec: float
    max_interval_sec: float
    last_run: float = 0.0
    run_count: int = 0


# Default intervals in seconds
_DEFAULT_TIERS: Dict[CadenceTier, TierConfig] = {
    CadenceTier.CRITICAL: TierConfig(
        base_interval_sec=300.0,    # 5 min
        min_interval_sec=60.0,      # 1 min (attack mode)
        max_interval_sec=600.0,     # 10 min (idle)
    ),
    CadenceTier.MAINTENANCE: TierConfig(
        base_interval_sec=900.0,    # 15 min
        min_interval_sec=180.0,     # 3 min (ABP)
        max_interval_sec=1800.0,    # 30 min (idle)
    ),
    CadenceTier.STRATEGIC: TierConfig(
        base_interval_sec=1800.0,   # 30 min
        min_interval_sec=300.0,     # 5 min (ABP)
        max_interval_sec=3600.0,    # 60 min (idle)
    ),
}


class AdaptiveCadenceManager:
    """
    Manages dynamic tick intervals for each subsystem tier.

    Usage:
        cadence = get_cadence_manager()
        if cadence.should_run_tier(CadenceTier.CRITICAL):
            # run verification, contamination defense
            cadence.mark_run(CadenceTier.CRITICAL)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.tiers: Dict[CadenceTier, TierConfig] = {
            tier: TierConfig(
                base_interval_sec=cfg.base_interval_sec,
                min_interval_sec=cfg.min_interval_sec,
                max_interval_sec=cfg.max_interval_sec,
            )
            for tier, cfg in _DEFAULT_TIERS.items()
        }
        self.mode: CadenceMode = CadenceMode.NORMAL
        self._mode_since: float = time.time()
        self._global_multiplier: float = 1.0
        self._attack_until: float = 0.0

    def set_mode(self, mode: CadenceMode, multiplier: float = 1.0) -> None:
        with self._lock:
            self.mode = mode
            self._mode_since = time.time()
            if mode == CadenceMode.ABP_BOOTSTRAP:
                self._global_multiplier = max(0.1, min(10.0, multiplier))
            elif mode == CadenceMode.ATTACK_RESPONSE:
                self._global_multiplier = 0.25
                self._attack_until = time.time() + 3600
            elif mode == CadenceMode.IDLE:
                self._global_multiplier = 2.0
            else:
                self._global_multiplier = 1.0

    def set_abp_multiplier(self, multiplier: float) -> None:
        """Called by ABP to set the acceleration factor (e.g., 4.0 = 4x faster)."""
        with self._lock:
            if self.mode == CadenceMode.ABP_BOOTSTRAP:
                self._global_multiplier = 1.0 / max(0.1, multiplier)

    def _effective_interval(self, tier: CadenceTier) -> float:
        cfg = self.tiers[tier]
        interval = cfg.base_interval_sec * self._global_multiplier

        if self.mode == CadenceMode.ATTACK_RESPONSE and tier == CadenceTier.CRITICAL:
            interval = cfg.min_interval_sec

        return max(cfg.min_interval_sec, min(cfg.max_interval_sec, interval))

    def should_run_tier(self, tier: CadenceTier) -> bool:
        """Check if enough time has elapsed since last run of this tier."""
        with self._lock:
            cfg = self.tiers[tier]
            now = time.time()
            interval = self._effective_interval(tier)
            return (now - cfg.last_run) >= interval

    def mark_run(self, tier: CadenceTier) -> None:
        """Record that a tier just ran."""
        with self._lock:
            cfg = self.tiers[tier]
            cfg.last_run = time.time()
            cfg.run_count += 1

    def check_attack_timeout(self) -> None:
        """Auto-revert from attack mode after timeout."""
        with self._lock:
            if (self.mode == CadenceMode.ATTACK_RESPONSE
                    and time.time() > self._attack_until):
                self.mode = CadenceMode.NORMAL
                self._global_multiplier = 1.0

    def status(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            tier_status = {}
            for tier, cfg in self.tiers.items():
                interval = self._effective_interval(tier)
                since_last = now - cfg.last_run if cfg.last_run > 0 else float("inf")
                tier_status[tier.value] = {
                    "effective_interval_sec": round(interval, 1),
                    "base_interval_sec": cfg.base_interval_sec,
                    "since_last_run_sec": round(since_last, 1),
                    "ready": since_last >= interval,
                    "run_count": cfg.run_count,
                }
            return {
                "mode": self.mode.value,
                "global_multiplier": round(self._global_multiplier, 3),
                "mode_since": self._mode_since,
                "tiers": tier_status,
            }


# ----------------------------------------------------------------
# GLOBAL INSTANCE
# ----------------------------------------------------------------

_cadence_manager = AdaptiveCadenceManager()


def get_cadence_manager() -> AdaptiveCadenceManager:
    return _cadence_manager
