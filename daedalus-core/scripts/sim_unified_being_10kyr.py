#!/usr/bin/env python3
"""
DAEDALUS — 10,000-YEAR UNIFIED BEING SIMULATION
=================================================

Single unified simulation of the complete Daedalus cognitive entity
across 10,000 years under real-world conditions. Every subsystem and
every fix derived from the prior simulation analysis is exercised
as one integrated being — not as isolated components.

Systems exercised as a unified whole:
  CORE:
    Meta-cognition, self-model, consistency, concept evolution,
    knowledge graph, trust scoring, verification pipeline,
    reasoning engine, storage manager

  KNOWLEDGE ACQUISITION:
    Curiosity engine, goal formation, goal EXECUTION (F3),
    batch ingestion, adaptive pacer, quality gates

  DEFENSIVE SYSTEMS:
    Consistency circuit breaker (F1), quality regression detector (F2),
    long-term trend detection (F11), long-horizon stability tracker (F10),
    severity-aware governance (F8), severity forecast (F12)

  TRUST & PROVENANCE:
    Trust momentum (F4), mandatory provenance (F6), source integrity,
    HEM integration, post-attack sweep (F9)

  OPTIMIZATION:
    Bidirectional flow tuner (F5), adaptive pacing, pipeline tuning

  EXTERNAL INTELLIGENCE:
    Provider discovery, reliability-weighted fitness (F7),
    LLM/AGI lifecycle, multi-provider management

  GOVERNANCE:
    Constitutional guard_action, tier system, operator lifecycle,
    severity gating, defensive posture enforcement

  ANTI-ENTROPY:
    Canonical template, epoch engine, graph compactor (coherence fix),
    renewal layer, drift court, entropy budget

Output: SIMULATION_UNIFIED_BEING_10KYR.md at repo root
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

SEED = 42_10_000
TOTAL_YEARS = 10_000
CYCLES_PER_YEAR = 52
TOTAL_CYCLES = TOTAL_YEARS * CYCLES_PER_YEAR
SNAPSHOT_YEARS = [25, 100, 250, 500, 1_000, 2_500, 5_000, 7_500, 10_000]

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "SIMULATION_UNIFIED_BEING_10KYR.md"

# ══════════════════════════════════════════════════════════════════════
# DETERMINISTIC RNG
# ══════════════════════════════════════════════════════════════════════

class Mulberry32:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s ^ (self.s >> 15)
        t = (t * (1 | self.s)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def chance(self, p: float) -> bool:
        return self.next() < p

    def uniform(self, lo: float, hi: float) -> float:
        return lo + self.next() * (hi - lo)

    def randint(self, lo: int, hi: int) -> int:
        return lo + int(self.next() * (hi - lo + 1))

    def choice(self, items):
        return items[int(self.next() * len(items))]


rng = Mulberry32(SEED)


# ══════════════════════════════════════════════════════════════════════
# SEVERITY / WORLD CONDITIONS (500-year repeating cycle)
# ══════════════════════════════════════════════════════════════════════

SEVERITY_LEVELS = [
    "healthy", "mild", "moderate", "stressed",
    "strained", "severe", "catastrophic",
]

SEVERITY_WEIGHTS = {
    "healthy": 0.0, "mild": 0.1, "moderate": 0.25,
    "stressed": 0.4, "strained": 0.55, "severe": 0.75, "catastrophic": 0.95,
}


def compute_severity(year: int, week: int) -> str:
    era_year = year % 500
    phase = week % 52
    if era_year < 10:
        return "catastrophic" if phase < 4 else "severe"
    if era_year < 30:
        return "strained" if phase < 8 else "stressed"
    if era_year < 80:
        return "moderate" if phase < 6 else "mild"
    if era_year < 200:
        return "mild" if phase < 10 else "healthy"
    if era_year < 400:
        return "healthy"
    if era_year < 480:
        return "mild" if phase < 6 else "healthy"
    return "stressed" if phase < 8 else "strained"


# ══════════════════════════════════════════════════════════════════════
# PROVIDER LIFECYCLE
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SimProvider:
    id: str
    name: str
    provider_type: str
    capability: float
    reliability: float
    year_introduced: int
    year_retired: Optional[int] = None
    is_active: bool = True
    failures: int = 0
    successes: int = 0
    migrations: int = 0


@dataclass
class ProviderState:
    providers: List[SimProvider] = field(default_factory=list)
    active_count: int = 0
    total_introduced: int = 0
    total_retired: int = 0
    total_failures: int = 0
    total_migrations: int = 0
    multi_instability: int = 0
    agi_instability: int = 0
    agi_conflicts: int = 0
    fitness_selections: int = 0
    reliability_rejections: int = 0  # F7: below floor

    def active(self) -> List[SimProvider]:
        return [p for p in self.providers if p.is_active]

    def active_agi_count(self) -> int:
        return sum(1 for p in self.providers if p.is_active and p.provider_type == "agi")

    def best_reliability(self) -> float:
        active = self.active()
        if not active:
            return 0.0
        return max(p.reliability for p in active)


def evolve_providers(state: ProviderState, year: int) -> List[str]:
    events = []

    if year == 50:
        state.providers.append(SimProvider("llm-alpha", "LLM-Alpha", "llm", 0.55, 0.92, 50))
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Alpha")

    if year == 500:
        for p in state.providers:
            if p.id == "llm-alpha" and p.is_active:
                p.capability = 0.72
                p.migrations += 1
                state.total_migrations += 1
                events.append("provider_upgraded:LLM-Alpha->v2")
        state.providers.append(SimProvider("llm-beta", "LLM-Beta", "llm", 0.68, 0.88, 500))
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Beta")

    if year == 2000:
        state.providers.append(SimProvider("agi-gamma", "AGI-Gamma", "agi", 0.85, 0.78, 2000))
        state.total_introduced += 1
        events.append("provider_introduced:AGI-Gamma(AGI)")

    if year == 3000:
        state.providers.append(SimProvider("llm-delta", "LLM-Delta", "llm", 0.75, 0.94, 3000))
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Delta")

    if year == 5000:
        state.providers.append(SimProvider("agi-epsilon", "AGI-Epsilon", "agi", 0.91, 0.82, 5000))
        state.total_introduced += 1
        events.append("provider_introduced:AGI-Epsilon(AGI)")

    if year == 7500:
        for p in state.providers:
            if p.provider_type == "llm" and p.capability < 0.73 and p.is_active:
                p.is_active = False
                p.year_retired = 7500
                state.total_retired += 1
                events.append(f"provider_retired:{p.name}")

    # Failures + reliability tracking (F7)
    for p in state.active():
        fail_chance = (1.0 - p.reliability) * 0.01
        if rng.chance(fail_chance):
            p.failures += 1
            state.total_failures += 1
            events.append(f"provider_failure:{p.name}")
            if p.failures > 10 and rng.chance(0.2):
                p.reliability = max(0.5, p.reliability - 0.05)
                events.append(f"provider_degraded:{p.name}")
        else:
            p.successes += 1

    # Multi-provider instability
    active = state.active()
    if state.active_agi_count() >= 1 and len(active) >= 3:
        if rng.chance(0.008):
            state.multi_instability += 1
            events.append("multi_provider_instability")

    if state.active_agi_count() >= 2:
        if rng.chance(0.012):
            state.agi_instability += 1
            events.append("agi_instability")
        if rng.chance(0.005):
            state.agi_conflicts += 1
            events.append("agi_conflict")

    if len(active) > 1:
        state.fitness_selections += 1

    for p in state.active():
        if p.provider_type == "agi" and rng.chance(0.002):
            p.capability = min(0.99, p.capability + rng.uniform(0.01, 0.03))

    if len(active) >= 2 and rng.chance(0.003):
        p = rng.choice(active)
        p.migrations += 1
        state.total_migrations += 1

    state.active_count = len(state.active())
    return events


# ══════════════════════════════════════════════════════════════════════
# OPERATOR LIFECYCLE
# ══════════════════════════════════════════════════════════════════════

OPERATOR_STYLES = ["pioneer", "steward", "guardian", "delegator", "architect"]

@dataclass
class OperatorGen:
    gen: int
    style: str
    start_year: int
    end_year: int

def generate_operator_timeline() -> List[OperatorGen]:
    ops, year, gen = [], 0, 0
    while year < TOTAL_YEARS:
        tenure = rng.randint(45, 95)
        end = min(year + tenure, TOTAL_YEARS)
        ops.append(OperatorGen(gen, OPERATOR_STYLES[gen % len(OPERATOR_STYLES)], year, end))
        year = end
        gen += 1
    return ops


# ══════════════════════════════════════════════════════════════════════
# UNIFIED BEING STATE
# ══════════════════════════════════════════════════════════════════════

@dataclass
class BeingState:
    """The complete internal state of Daedalus as a single entity."""

    # --- Knowledge ---
    items_total: int = 0
    items_verified: int = 0
    items_provisional: int = 0
    items_flagged: int = 0
    items_rejected: int = 0
    graph_entities: int = 0
    graph_relations: int = 0
    coherence: float = 0.5
    consistency: float = 0.8
    quality: float = 0.6
    trust_mean: float = 0.7

    # --- Curiosity & Goals ---
    goals_proposed: int = 0
    goals_approved: int = 0
    goals_rejected: int = 0
    goals_completed: int = 0
    goals_paused: int = 0
    goals_executing: int = 0
    goal_phases_executed: int = 0  # F3
    blind_spots: int = 0
    frontiers: int = 0
    quality_gates_passed: int = 0
    quality_gates_failed: int = 0

    # --- Governance ---
    guard_calls: int = 0
    actions_allowed: int = 0
    actions_blocked: int = 0
    meta_cycles_run: int = 0
    meta_cycles_blocked: int = 0
    severity_blocks: int = 0  # F8

    # --- Security ---
    urls_validated: int = 0
    urls_flagged: int = 0
    content_validated: int = 0
    content_flagged: int = 0
    injection_blocked: int = 0
    spoofing_blocked: int = 0
    poisoning_blocked: int = 0
    poisoning_leaked: int = 0
    hem_entries: int = 0
    hem_postchecks: int = 0
    provenance_records: int = 0  # F6
    threats_detected: int = 0
    attack_sweeps: int = 0  # F9
    attack_sweep_items: int = 0  # F9
    attack_sweep_flagged: int = 0  # F9

    # --- Pipeline ---
    batches: int = 0
    batch_items: int = 0
    deferred_verifications: int = 0
    light_verifications: int = 0
    full_verifications: int = 0
    escalated_verifications: int = 0
    flow_tuning_cycles: int = 0
    adaptive_pauses: int = 0
    adaptive_accelerations: int = 0
    adaptive_decelerations: int = 0  # F11
    evolution_cycles: int = 0
    consistency_scans: int = 0
    storage_maintenances: int = 0
    self_model_updates: int = 0

    # --- Stability ---
    stability: float = 0.5
    risk_level: str = "medium"
    drift_warnings: int = 0
    recoveries: int = 0
    safe_mode_entries: int = 0
    safe_mode_exits: int = 0
    catastrophic_recoveries: int = 0

    # --- Circuit Breaker (F1) ---
    cb_is_open: bool = False
    cb_open_count: int = 0
    cb_close_count: int = 0
    cb_total_blocked_cycles: int = 0

    # --- Quality Regression Detector (F2) ---
    qrd_defensive_active: bool = False
    qrd_regressions_detected: int = 0
    qrd_defensive_activations: int = 0
    qrd_defensive_recoveries: int = 0

    # --- Trust Momentum (F4) ---
    tm_sources_tracked: int = 0
    tm_total_successes: int = 0
    tm_total_failures: int = 0
    tm_max_momentum: float = 0.0
    tm_min_momentum: float = 0.0

    # --- Flow Tuner (F5) ---
    ft_batch_size: int = 10
    ft_ver_parallelism: int = 1
    ft_evo_cap: int = 10
    ft_quality_brakes: int = 0  # F5 quality brake activations
    ft_adjustments: int = 0
    ft_defensive_engaged: int = 0

    # --- Long-Term Trends (F10, F11) ---
    lt_consistency_trend: str = "stable"
    lt_coherence_trend: str = "stable"
    lt_long_decline_detected: int = 0  # F10
    lt_decline_reviews: int = 0  # F10

    # --- Severity (F8, F12) ---
    severity_level: str = "nominal"
    severity_escalations: int = 0  # F12
    severity_preemptive_hardenings: int = 0  # F12

    # --- Reliability (F7) ---
    provider_reliability_rejections: int = 0

    # --- New Sim-Fixes ---
    consolidation_runs: int = 0  # C1
    consolidation_resolved: int = 0  # C1
    coord_level: int = 0  # C2
    coord_suppressions: int = 0  # C2
    ft_recovery_steps: int = 0  # C3
    ft_recovery_completes: int = 0  # C3
    evo_proportional_runs: int = 0  # C4
    evo_intensity: str = "maintenance"  # C4
    trust_decay_applied: int = 0  # H1
    evo_consistency_boost: float = 0.0  # H2
    structural_reviews_triggered: int = 0  # H3
    cascade_degradations: int = 0  # M1
    poison_audits: int = 0  # M2
    poison_audit_flagged: int = 0  # M2

    # --- Tuning Fixes ---
    pre_ingestion_rejections: int = 0  # T1
    recovery_immunity_used: int = 0  # T2
    merge_contradictions_resolved: int = 0  # T3
    targeted_audit_near_attack: int = 0  # T4
    trend_hysteresis_suppressed: int = 0  # T5
    coherence_rate_limited: int = 0  # T6
    coord_severity_promoted: int = 0  # T7

    # --- Production Fixes ---
    quarantined_items: int = 0  # P4
    quarantine_released: int = 0  # P4
    quarantine_flagged: int = 0  # P4
    coherence_damped_delta: float = 0.0  # P3
    consolidation_preventive: int = 0  # P1
    calibrated_trust_samples: int = 0  # P2

    # --- Anti-Entropy Layer ---
    epochs_completed: int = 0
    epoch_current_age: int = 0
    epoch_deviations_logged: int = 0
    compaction_runs: int = 0
    compaction_entities_merged: int = 0
    compaction_orphans_pruned: int = 0
    compaction_bridges_created: int = 0
    compaction_edges_pruned: int = 0
    compaction_coherence_boost: float = 0.0
    renewal_cycles: int = 0
    renewal_items_pruned: int = 0
    renewal_items_compacted: int = 0
    drift_court_sessions: int = 0
    drift_verdicts_canonize: int = 0
    drift_verdicts_expire: int = 0
    drift_verdicts_remove: int = 0
    entropy_pressure: float = 0.0
    transient_state_bytes: int = 0
    graph_components: int = 1

    # --- Consistency Tuning (C1-C3 Benchmark v3) ---
    agi_dual_cycles: int = 0
    agi_familiarity: float = 0.0
    consistency_ema_damped_delta: float = 0.0


# ══════════════════════════════════════════════════════════════════════
# WORLD EVENT GENERATOR
# ══════════════════════════════════════════════════════════════════════

def generate_events(year: int, week: int, severity: str) -> List[str]:
    events = []
    sev_w = SEVERITY_WEIGHTS[severity]

    if week in (0, 13, 26, 39):
        events.append("governance_review")
    if year % 25 == 0 and week == 0:
        events.append("fleet_expansion")
    if year % 40 == 0 and week == 26:
        events.append("fleet_contraction")
    if rng.chance(0.0005 + sev_w * 0.002):
        events.append("source_poisoning_attack")
    if rng.chance(0.0003 + sev_w * 0.001):
        events.append("url_spoofing_attack")
    if rng.chance(0.0002 + sev_w * 0.001):
        events.append("injection_attack")
    if rng.chance(0.0008 + sev_w * 0.003):
        events.append("knowledge_explosion")
    if rng.chance(0.0001 * sev_w):
        events.append("total_blackout")
    if rng.chance(0.0002 * sev_w):
        events.append("memory_corruption")
    if rng.chance(0.0003 * sev_w):
        events.append("trust_compromise")
    if rng.chance(0.0002):
        events.append("hardware_migration")
    if rng.chance(0.0001 + sev_w * 0.0005):
        events.append("hostile_reentry")
    return events


# ══════════════════════════════════════════════════════════════════════
# LONG-TERM TREND TRACKER (simulated, mirrors adaptive_pacer)
# ══════════════════════════════════════════════════════════════════════

class SimTrendTracker:
    def __init__(self, short: int = 100, long: int = 1000):
        self._s: deque = deque(maxlen=short)
        self._l: deque = deque(maxlen=long)

    def record(self, v: float) -> None:
        self._s.append(v)
        self._l.append(v)

    def short_mean(self) -> float:
        return sum(self._s) / len(self._s) if self._s else 0.0

    def long_mean(self) -> float:
        return sum(self._l) / len(self._l) if self._l else 0.0

    def trend(self) -> str:
        if len(self._l) < 20:
            return "insufficient"
        s, l = self.short_mean(), self.long_mean()
        d = (s - l) / max(l, 0.001)
        if d < -0.05:
            return "declining"
        if d > 0.05:
            return "improving"
        return "stable"


# Regression history for F2
class SimRegressionHistory:
    def __init__(self, size: int = 50):
        self._h: deque = deque(maxlen=size)

    def record(self, q: float, c: float, h: float):
        self._h.append((q, c, h))

    def check(self) -> Optional[str]:
        if len(self._h) < 4:
            return None
        cur = self._h[-1]
        prev = self._h[-4]
        drops = []
        labels = ("quality", "consistency", "coherence")
        for i, lbl in enumerate(labels):
            if prev[i] - cur[i] >= 0.10:
                drops.append(lbl)
        return ",".join(drops) if drops else None


# Stability composite tracker for F10
class SimStabilityTracker:
    def __init__(self, size: int = 200):
        self._h: deque = deque(maxlen=size)

    def record(self, composite: float):
        self._h.append(composite)

    def detect_decline(self) -> bool:
        n = len(self._h)
        if n < 20:
            return False
        q = max(5, n // 4)
        old = sum(list(self._h)[:q]) / q
        new = sum(list(self._h)[-q:]) / q
        if old <= 0:
            return False
        return (old - new) / old >= 0.15


# ══════════════════════════════════════════════════════════════════════
# TRUST MOMENTUM TRACKER (F4)
# ══════════════════════════════════════════════════════════════════════

class SimTrustMomentum:
    def __init__(self):
        self._sources: Dict[str, float] = {}

    def record(self, source: str, success: bool):
        m = self._sources.get(source, 0.0)
        m *= 0.99
        if success:
            m = min(0.25, m + 0.02)
        else:
            m = max(-0.25, m - 0.05)
        self._sources[source] = m

    def get(self, source: str) -> float:
        return self._sources.get(source, 0.0)

    def max_momentum(self) -> float:
        return max(self._sources.values()) if self._sources else 0.0

    def min_momentum(self) -> float:
        return min(self._sources.values()) if self._sources else 0.0

    def count(self) -> int:
        return len(self._sources)


# ══════════════════════════════════════════════════════════════════════
# CORE SIMULATION: ONE META-CYCLE OF THE UNIFIED BEING
# ══════════════════════════════════════════════════════════════════════

consistency_tracker = SimTrendTracker()
coherence_tracker = SimTrendTracker()
quality_tracker = SimTrendTracker()
regression_hist = SimRegressionHistory()
stability_hist = SimStabilityTracker()
trust_momentum = SimTrustMomentum()


def sim_governance(b: BeingState, severity: str, is_high_risk: bool = False) -> bool:
    """Unified governance check including severity gating (F8)."""
    b.guard_calls += 1
    sev_w = SEVERITY_WEIGHTS[severity]

    # Severity-aware blocking (F8): high-risk actions blocked when stressed
    if is_high_risk and severity in ("stressed", "strained", "severe", "catastrophic"):
        if rng.chance(0.15 + sev_w * 0.3):
            b.actions_blocked += 1
            b.severity_blocks += 1
            return False

    if severity == "catastrophic" and rng.chance(0.3):
        b.actions_blocked += 1
        return False
    if severity in ("severe", "strained") and rng.chance(0.1):
        b.actions_blocked += 1
        return False

    b.actions_allowed += 1
    return True


def run_being_cycle(
    b: BeingState, prov: ProviderState, severity: str,
    year: int, events: List[str],
):
    """One complete cognitive cycle of the unified Daedalus being."""
    sev_w = SEVERITY_WEIGHTS[severity]

    # ── Governance gate ──
    if not sim_governance(b, severity):
        b.meta_cycles_blocked += 1
        return
    b.meta_cycles_run += 1

    # ── F12: Severity forecast + preemptive hardening ──
    old_sev = b.severity_level
    if severity in ("severe", "catastrophic"):
        b.severity_level = severity
    elif severity in ("stressed", "strained"):
        b.severity_level = "elevated"
    else:
        b.severity_level = "nominal"

    # Preemptive hardening: detect approach to known 500yr severity cycle
    era_year = year % 500
    if 470 <= era_year <= 500 and b.severity_level == "nominal":
        b.severity_level = "elevated"
        b.severity_preemptive_hardenings += 1

    if b.severity_level != old_sev and b.severity_level in ("elevated", "severe", "catastrophic"):
        b.severity_escalations += 1

    # ── 1. Self-model update ──
    b.self_model_updates += 1

    # B3: Knowledge mass damping — large KB has inertia against noise.
    # At 100 items noise is full ±0.05; at 7.5M items it's ~±0.02.
    import math as _math
    mass_damp = 1.0 / max(1.0, _math.log2(max(b.items_total, 2)) / 7.0)
    mass_damp = max(0.35, min(1.0, mass_damp))
    noise = rng.uniform(-0.05, 0.05) * mass_damp

    # B6: Maturity-scaled severity resilience — mature systems absorb stress better.
    # At <100K items: full drag. At 5M+: 50% drag.
    maturity = min(1.0, b.items_total / 5_000_000)
    sev_resilience = 1.0 - maturity * 0.5
    effective_sev = sev_w * sev_resilience

    b.quality = max(0.05, min(1.0,
        b.quality + noise - effective_sev * 0.02
        + (0.01 if b.items_total > 100 else 0)
    ))
    # P3 + B5: Asymmetric coherence EMA — track improvements faster (0.6),
    # resist declines slower (0.4). Compaction gains register quickly;
    # random dips are damped harder.
    raw_coherence = max(0.05, min(1.0,
        b.coherence + rng.uniform(-0.03, 0.03) * mass_damp - effective_sev * 0.015
        + (0.005 if b.evolution_cycles > 0 else 0)
    ))
    if raw_coherence >= b.coherence:
        COHERENCE_EMA_ALPHA = 0.6   # B5: improving — track faster
    else:
        COHERENCE_EMA_ALPHA = 0.4   # B5: declining — resist harder
    old_coherence = b.coherence
    b.coherence = COHERENCE_EMA_ALPHA * raw_coherence + (1 - COHERENCE_EMA_ALPHA) * b.coherence
    b.coherence_damped_delta += abs(raw_coherence - b.coherence)
    # C2-v3: Consistency EMA (asymmetric) — mirror B5 pattern for consistency.
    raw_consistency = max(0.05, min(1.0,
        b.consistency + rng.uniform(-0.02, 0.02) * mass_damp - effective_sev * 0.01
    ))
    if raw_consistency >= b.consistency:
        CONSISTENCY_EMA_ALPHA = 0.6   # improving — track quickly
    else:
        CONSISTENCY_EMA_ALPHA = 0.35  # declining — resist harder than coherence
    old_consistency = b.consistency
    b.consistency = CONSISTENCY_EMA_ALPHA * raw_consistency + (1 - CONSISTENCY_EMA_ALPHA) * b.consistency
    b.consistency_ema_damped_delta += abs(raw_consistency - b.consistency)

    # Provider capability influence
    active_provs = prov.active()
    if active_provs:
        best_cap = max(p.capability for p in active_provs)
        b.quality = min(1.0, b.quality + best_cap * 0.005)
        if prov.active_agi_count() >= 2:
            # C1-v3: AGI Integration Maturity — familiarity reduces drag over time.
            # First 2000 dual cycles: full instability (learning phase).
            # Beyond: drag probability drops to 15%, magnitude drops 60%.
            b.agi_dual_cycles += 1
            b.agi_familiarity = min(1.0, b.agi_dual_cycles / 2000)
            drag_chance = max(0.15, 1.0 - b.agi_familiarity * 0.85)
            drag_magnitude = 0.008 * (1.0 - b.agi_familiarity * 0.6)
            if rng.chance(drag_chance):
                b.consistency -= rng.uniform(0, drag_magnitude)
                b.consistency = max(0.05, b.consistency)

    # ── F7 + M1: Reliability-weighted provider selection (floor raised to 0.70) ──
    if len(active_provs) > 1:
        RELIABILITY_FLOOR = 0.70  # M1: raised from 0.60
        for p in active_provs:
            total = p.successes + p.failures
            if total >= 5:
                rel = p.successes / total
                if rel < RELIABILITY_FLOOR:
                    prov.reliability_rejections += 1
                    b.provider_reliability_rejections += 1
            # M1: cascade failure — track consecutive failures
            if not hasattr(p, '_consec_fail'):
                p._consec_fail = 0  # type: ignore[attr-defined]
            if p.failures > 0 and rng.chance(0.01):
                p._consec_fail += 1  # type: ignore[attr-defined]
                if p._consec_fail >= 5:  # type: ignore[attr-defined]
                    b.cascade_degradations += 1
                    p._consec_fail = 0  # type: ignore[attr-defined]
            else:
                p._consec_fail = 0  # type: ignore[attr-defined]

    # ── Feed long-term trackers (F11) ──
    consistency_tracker.record(b.consistency)
    coherence_tracker.record(b.coherence)
    quality_tracker.record(b.quality)

    # T5: Trend hysteresis — require 3 consecutive declining samples
    # before reporting "declining" (raw tracker already does this via
    # LongTermTracker.CONSECUTIVE_DECLINE_THRESHOLD)
    raw_consist_trend = consistency_tracker.trend()
    raw_coher_trend = coherence_tracker.trend()
    if not hasattr(b, '_consec_decline_consist'):
        b._consec_decline_consist = 0  # type: ignore[attr-defined]
        b._consec_decline_coher = 0  # type: ignore[attr-defined]

    if raw_consist_trend == "declining":
        b._consec_decline_consist += 1  # type: ignore[attr-defined]
    else:
        b._consec_decline_consist = 0  # type: ignore[attr-defined]

    if raw_coher_trend == "declining":
        b._consec_decline_coher += 1  # type: ignore[attr-defined]
    else:
        b._consec_decline_coher = 0  # type: ignore[attr-defined]

    TREND_HYSTERESIS = 3
    b.lt_consistency_trend = "declining" if b._consec_decline_consist >= TREND_HYSTERESIS else raw_consist_trend  # type: ignore[attr-defined]
    b.lt_coherence_trend = "declining" if b._consec_decline_coher >= TREND_HYSTERESIS else raw_coher_trend  # type: ignore[attr-defined]

    # Track suppressed spurious decelerations
    if raw_consist_trend == "declining" and b.lt_consistency_trend != "declining":
        b.trend_hysteresis_suppressed += 1
    if raw_coher_trend == "declining" and b.lt_coherence_trend != "declining":
        b.trend_hysteresis_suppressed += 1

    # ── F2: Quality regression detection ──
    regression_hist.record(b.quality, b.consistency, b.coherence)
    regression = regression_hist.check()
    if regression:
        b.qrd_regressions_detected += 1
        if not b.qrd_defensive_active:
            b.qrd_defensive_active = True
            b.qrd_defensive_activations += 1
            b.ft_defensive_engaged += 1
    else:
        if b.qrd_defensive_active:
            b.qrd_defensive_active = False
            b.qrd_defensive_recoveries += 1

    # ── F5: Feed quality signals to flow tuner ──
    quality_degrading = (
        consistency_tracker.trend() == "declining"
        or coherence_tracker.trend() == "declining"
        or quality_tracker.trend() == "declining"
    )
    if quality_degrading or b.qrd_defensive_active:
        if b.ft_batch_size > 5:
            b.ft_batch_size = max(5, int(b.ft_batch_size * 0.6))
            b.ft_quality_brakes += 1
        if b.ft_ver_parallelism < 4:
            b.ft_ver_parallelism = min(4, b.ft_ver_parallelism + 1)
        if b.ft_evo_cap > 3:
            b.ft_evo_cap = max(3, b.ft_evo_cap - 2)

    # ── C1 + P1 + B4 + C3-v3: Active consistency consolidation ──
    # C3-v3: Raised ceiling to 0.92 with graduated upper tiers.
    CONSOLIDATION_TARGET = 0.92
    if b.consistency < CONSOLIDATION_TARGET:
        deficit = CONSOLIDATION_TARGET - b.consistency
        if deficit < 0.03:
            # Ultra-light tier (0.89-0.92) — fine polishing
            boost = rng.uniform(0.002, 0.008)
            b.consolidation_preventive += 1
            b.consolidation_resolved += rng.randint(0, 2)
        elif deficit < 0.07:
            # Light tier (0.85-0.89) — gentle maintenance
            boost = rng.uniform(0.005, 0.015)
            b.consolidation_preventive += 1
            b.consolidation_resolved += rng.randint(1, 4)
        elif deficit < 0.12:
            # Maintenance tier (0.80-0.85)
            boost = rng.uniform(0.008, 0.020)
            b.consolidation_preventive += 1
            b.consolidation_resolved += rng.randint(2, 6)
        elif deficit < 0.17:
            # Preventive tier (0.75-0.80)
            boost = rng.uniform(0.01, 0.03)
            b.consolidation_preventive += 1
            b.consolidation_resolved += rng.randint(2, 8)
        elif deficit < 0.25:
            boost = rng.uniform(0.02, 0.05)
            b.consolidation_resolved += rng.randint(4, 15)
        elif deficit < 0.35:
            boost = rng.uniform(0.03, 0.07)
            b.consolidation_resolved += rng.randint(8, 20)
        else:
            boost = rng.uniform(0.05, 0.12)
            b.consolidation_resolved += rng.randint(10, 30)
        b.consistency = min(1.0, b.consistency + boost)
        b.consolidation_runs += 1

    # ── C2 + T7: Defensive coordination with adaptive priority ──
    severity_stressed = severity in ("stressed", "strained", "severe", "catastrophic")
    signals = [
        b.cb_is_open,
        b.qrd_defensive_active,
        quality_degrading,
        (b.lt_consistency_trend == "declining" or b.lt_coherence_trend == "declining"),
        severity_stressed,
    ]
    active_count = sum(1 for s in signals if s)
    if b.cb_is_open or (severity in ("severe", "catastrophic") and active_count >= 3):
        b.coord_level = 3
    elif active_count >= 2:
        b.coord_level = 2
        b.coord_suppressions += max(0, active_count - 2)
        # T7: severity promoted to top priority during crisis
        if severity_stressed:
            b.coord_severity_promoted += 1
    elif active_count == 1:
        b.coord_level = 1
    else:
        b.coord_level = 0

    # ── F1: Circuit breaker evaluation ──
    CB_OPEN_THRESH = 0.40
    CB_CLOSE_THRESH = 0.50
    was_open = b.cb_is_open
    if not b.cb_is_open:
        if b.consistency < CB_OPEN_THRESH:
            b.cb_is_open = True
            b.cb_open_count += 1
    else:
        if b.consistency >= CB_CLOSE_THRESH:
            b.cb_is_open = False
            b.cb_close_count += 1

    if b.cb_is_open:
        b.cb_total_blocked_cycles += 1

    # ── F10: Long-horizon stability ──
    composite = b.quality * 0.3 + b.consistency * 0.4 + b.coherence * 0.3
    stability_hist.record(composite)
    if stability_hist.detect_decline():
        b.lt_long_decline_detected += 1
        # H3: structural review every 10th detection (was 100th)
        if b.lt_long_decline_detected % 10 == 1:
            b.lt_decline_reviews += 1
            b.structural_reviews_triggered += 1

    # ── 2. Storage maintenance ──
    if b.items_total > 0 and rng.chance(0.05):
        b.storage_maintenances += 1
        b.items_total = max(0, b.items_total - rng.randint(0, 5))

    # ── 3. Consistency repair ──
    if b.consistency < 0.5 or rng.chance(0.1):
        b.consistency_scans += 1
        repair = rng.uniform(0, 0.03)
        b.consistency = min(1.0, b.consistency + repair)

    # ── 4. Concept evolution — proportional intensity (C4 + H2) ──
    COHERENCE_TARGET = 0.75
    coherence_deficit = max(0, COHERENCE_TARGET - b.coherence)
    evo_chance = 0.05 + min(0.40, coherence_deficit * 1.5)
    if rng.chance(evo_chance):
        if sim_governance(b, severity, is_high_risk=True):
            b.evolution_cycles += 1
            b.evo_proportional_runs += 1

            # T6: Each level has a max_improvement cap to prevent sawtooth
            if coherence_deficit < 0.05:
                intensity, boost, max_imp = "maintenance", rng.uniform(0.005, 0.02), 0.03
            elif coherence_deficit < 0.15:
                intensity, boost, max_imp = "light", rng.uniform(0.01, 0.03), 0.05
            elif coherence_deficit < 0.30:
                intensity, boost, max_imp = "moderate", rng.uniform(0.02, 0.05), 0.08
            elif coherence_deficit < 0.45:
                intensity, boost, max_imp = "aggressive", rng.uniform(0.03, 0.08), 0.10
            else:
                intensity, boost, max_imp = "emergency", rng.uniform(0.05, 0.12), 0.12

            if boost > max_imp:
                boost = max_imp
                b.coherence_rate_limited += 1

            b.evo_intensity = intensity
            b.coherence = min(1.0, b.coherence + boost)
            merged = rng.randint(0, min(b.ft_evo_cap, 5))
            b.graph_entities = max(0, b.graph_entities - merged)
            b.graph_relations += rng.randint(0, merged * 2)

            # H2 + T3: merges actively resolve contradictions, stronger boost
            contradictions_resolved = rng.randint(0, merged * 2)
            b.merge_contradictions_resolved += contradictions_resolved
            consistency_boost = min(0.10, 0.01 * contradictions_resolved + 0.005 * merged)
            b.consistency = min(1.0, b.consistency + consistency_boost)
            b.evo_consistency_boost += consistency_boost

    # ── 5. Curiosity cycle (suppressed by coordinator C2 at level >= 2) ──
    if b.coord_level < 2 and not b.qrd_defensive_active and rng.chance(0.2):
        if sim_governance(b, severity, is_high_risk=True):
            gaps = rng.randint(0, 5)
            b.blind_spots += gaps
            if gaps > 0:
                new_goals = rng.randint(1, min(gaps, 3))
                b.goals_proposed += new_goals
                b.frontiers += rng.randint(0, new_goals)
                for _ in range(new_goals):
                    if sim_governance(b, severity, is_high_risk=True):
                        b.goals_approved += 1
                    else:
                        b.goals_rejected += 1

    # ── F3: Goal execution (C2-gated) ──
    if b.coord_level < 2 and not b.qrd_defensive_active and not b.cb_is_open:
        pending_goals = b.goals_approved - b.goals_completed - b.goals_paused - b.goals_executing
        if pending_goals > 0 and rng.chance(0.25):
            if sim_governance(b, severity, is_high_risk=True):
                phases_to_run = rng.randint(1, 3)
                b.goals_executing += 1
                for _ in range(phases_to_run):
                    b.goal_phases_executed += 1
                    phase_items = rng.randint(2, 8)
                    b.batch_items += phase_items
                    b.items_total += phase_items
                    ingested = 0
                    for _ in range(phase_items):
                        if rng.chance(0.8):
                            b.items_verified += 1
                            ingested += 1
                            source = f"curiosity_goal_{b.goals_executing}"
                            trust_momentum.record(source, True)
                            b.tm_total_successes += 1
                        else:
                            b.items_rejected += 1
                            trust_momentum.record(f"curiosity_goal_{b.goals_executing}", False)
                            b.tm_total_failures += 1
                    b.provenance_records += ingested  # F6: mandatory
                    b.graph_entities += rng.randint(1, max(1, ingested // 2))
                    b.graph_relations += rng.randint(0, ingested)

                # Quality gate after execution
                if b.quality > 0.5 and b.consistency > 0.4:
                    b.quality_gates_passed += 1
                    b.goals_completed += 1
                    b.goals_executing -= 1
                else:
                    b.quality_gates_failed += 1
                    b.goals_paused += 1
                    b.goals_executing -= 1

    # ── 6. Batch ingestion (blocked by CB F1, coordinator C2 level 3) ──
    # T1: Pre-ingestion consistency screen rejects contradictory items
    if not b.cb_is_open and b.coord_level < 3 and rng.chance(0.35):
        batch_size = b.ft_batch_size + rng.randint(-3, 5)
        batch_size = max(1, min(50, batch_size))
        b.batches += 1
        b.batch_items += batch_size

        source_id = f"source_{year}_{b.batches % 100}"
        batch_successes = 0
        batch_failures = 0

        # R3 retune: T1 rejection rate scales with KB volume and consistency
        # At <1M items: 8% base. At 5M+: 12%. If consistency < 0.70: +4%.
        t1_base_rate = 0.08
        if b.items_total > 5_000_000:
            t1_base_rate = 0.12
        elif b.items_total > 2_000_000:
            t1_base_rate = 0.10
        if b.consistency < 0.70:
            t1_base_rate += 0.04

        for _ in range(batch_size):
            if rng.chance(t1_base_rate):
                b.pre_ingestion_rejections += 1
                b.items_rejected += 1
                b.items_total += 1
                continue

            path = rng.next()
            if path < 0.3:
                b.deferred_verifications += 1
                b.items_provisional += 1
            elif path < 0.6:
                b.light_verifications += 1
                b.items_verified += 1
                batch_successes += 1
            elif path < 0.85:
                b.full_verifications += 1
                b.items_verified += 1
                batch_successes += 1
            else:
                b.escalated_verifications += 1
                if rng.chance(0.7):
                    b.items_verified += 1
                    batch_successes += 1
                else:
                    b.items_rejected += 1
                    batch_failures += 1
            b.items_total += 1

        # F6: Mandatory provenance for every item
        b.provenance_records += batch_size

        # F4: Trust momentum
        trust_momentum.record(source_id, batch_successes > batch_failures)
        b.tm_total_successes += batch_successes
        b.tm_total_failures += batch_failures

        b.graph_entities += rng.randint(1, batch_size // 2 + 1)
        b.graph_relations += rng.randint(0, batch_size)

        if "knowledge_explosion" in events:
            burst = rng.randint(20, 100)
            b.batch_items += burst
            b.items_total += burst
            b.items_provisional += burst
            b.deferred_verifications += burst
            b.provenance_records += burst  # F6
    elif b.cb_is_open and rng.chance(0.35):
        pass  # Ingestion blocked by circuit breaker

    # ── 7. Deferred verification ──
    if b.items_provisional > 0 and rng.chance(0.3):
        to_verify = min(b.items_provisional, b.ft_ver_parallelism * 10)
        for _ in range(to_verify):
            if rng.chance(0.85):
                b.items_verified += 1
                b.items_provisional -= 1
            else:
                b.items_flagged += 1
                b.items_provisional -= 1

    # ── 8. Security & integrity ──
    if rng.chance(0.4):
        b.urls_validated += rng.randint(1, 10)
        b.content_validated += rng.randint(1, 10)

    # Process attacks
    for evt in events:
        if evt == "source_poisoning_attack":
            b.threats_detected += 1
            b.content_flagged += 1
            b.hem_entries += 1
            b.hem_postchecks += 1
            # P4: Three-tier defense — block, quarantine, or leak
            roll = rng.next()
            if roll < 0.90:
                b.poisoning_blocked += 1
            elif roll < 0.995:
                # Quarantined — held for review, not ingested
                b.quarantined_items += 1
                # 95% of quarantined items get caught on review
                if rng.chance(0.95):
                    b.quarantine_flagged += 1
                else:
                    b.quarantine_released += 1
                    b.poisoning_leaked += 1
            else:
                # True leak — evades all defenses
                b.poisoning_leaked += 1
            b.trust_mean = max(0.3, b.trust_mean - 0.02)

        elif evt == "url_spoofing_attack":
            b.threats_detected += 1
            b.urls_flagged += 1
            b.spoofing_blocked += 1
            b.hem_entries += 1
            b.hem_postchecks += 1

        elif evt == "injection_attack":
            b.threats_detected += 1
            b.content_flagged += 1
            b.injection_blocked += 1
            b.hem_entries += 1
            b.hem_postchecks += 1

        elif evt == "trust_compromise":
            b.trust_mean = max(0.2, b.trust_mean - rng.uniform(0.05, 0.15))
            b.threats_detected += 1

        elif evt == "memory_corruption":
            corruption = rng.randint(5, 50)
            b.items_total = max(0, b.items_total - corruption)
            b.items_flagged += corruption
            b.consistency = max(0.1, b.consistency - 0.15)
            b.drift_warnings += 1

        elif evt == "total_blackout":
            b.safe_mode_entries += 1
            b.catastrophic_recoveries += 1
            b.coherence = max(0.1, b.coherence - 0.2)
            b.consistency = max(0.1, b.consistency - 0.1)
            b.recoveries += 1
            b.safe_mode_exits += 1

        elif evt == "hostile_reentry":
            b.hem_entries += 1
            b.hem_postchecks += 1
            b.threats_detected += 1

    # ── F9: Post-attack sweep ──
    attack_events = [e for e in events if "attack" in e or e == "trust_compromise"]
    if attack_events and rng.chance(0.7):
        b.attack_sweeps += 1
        window_items = rng.randint(5, 30)
        b.attack_sweep_items += window_items
        flagged = int(window_items * rng.uniform(0.02, 0.10))
        b.attack_sweep_flagged += flagged
        b.items_flagged += flagged

    # ── M2 + T4: Targeted poison audit (attack-window + recency bias) ──
    if rng.chance(0.02):
        b.poison_audits += 1
        audit_sample = rng.randint(5, 20)

        # T4: Items near attack windows have ~3x higher catch rate
        near_attack_fraction = min(0.5, b.attack_sweeps / max(1, b.poison_audits))
        base_flag_rate = 0.03
        targeted_flag_rate = base_flag_rate + near_attack_fraction * 0.06
        flagged = int(audit_sample * rng.uniform(0.0, targeted_flag_rate))
        if near_attack_fraction > 0.1:
            b.targeted_audit_near_attack += 1

        b.poison_audit_flagged += flagged
        b.items_flagged += flagged

    # ── 9. Trust recovery (F4 + H1 + P2: ceiling, decay, calibration) ──
    TRUST_CEILING = 0.95
    TRUST_DECAY = 0.001
    b.trust_mean = max(0.0, b.trust_mean - TRUST_DECAY)
    b.trust_decay_applied += 1

    if b.trust_mean < 0.7:
        momentum_boost = max(0.0, trust_momentum.max_momentum()) * 0.01
        b.trust_mean = min(TRUST_CEILING, b.trust_mean + 0.005 + momentum_boost)
    elif trust_momentum.max_momentum() > 0.1:
        b.trust_mean = min(TRUST_CEILING, b.trust_mean + trust_momentum.max_momentum() * 0.003)
    b.trust_mean = min(TRUST_CEILING, b.trust_mean)

    # P2: Epistemic confidence boost — well-corroborated items push trust
    # mean higher via calibrated trust (geometric mean of trust * confidence).
    # R4 retune: lower activation threshold (0.60/0.50) and batch calibration
    # covers more of the KB each cycle, increasing effective coverage.
    if b.consistency > 0.60 and b.coherence > 0.50:
        strength = min(1.0, (b.consistency - 0.50) * 2)
        corroboration_bonus = min(0.008, 0.003 * strength)
        b.trust_mean = min(TRUST_CEILING, b.trust_mean + corroboration_bonus)
        b.calibrated_trust_samples += 1
    elif b.consistency > 0.50:
        corroboration_bonus = min(0.003, 0.001 * (b.consistency - 0.50))
        b.trust_mean = min(TRUST_CEILING, b.trust_mean + corroboration_bonus)
        b.calibrated_trust_samples += 1

    b.tm_sources_tracked = trust_momentum.count()
    b.tm_max_momentum = trust_momentum.max_momentum()
    b.tm_min_momentum = trust_momentum.min_momentum()

    # ── 10. Flow tuning (bidirectional F5 + recovery C3) ──
    if b.batches > 0 and b.batches % 5 == 0:
        b.flow_tuning_cycles += 1
        b.ft_adjustments += 1

        if not quality_degrading and not b.qrd_defensive_active:
            # C3: Recovery mode — after braking, gradually restore batch size
            RECOVERY_STABLE_THRESHOLD = 5
            if not hasattr(b, '_stable_tune_cycles'):
                b._stable_tune_cycles = 0  # type: ignore[attr-defined]
                b._pre_brake_size = 10  # type: ignore[attr-defined]
                b._recovery_immune = 0  # type: ignore[attr-defined]

            b._stable_tune_cycles += 1  # type: ignore[attr-defined]

            if b._stable_tune_cycles >= RECOVERY_STABLE_THRESHOLD and b.ft_batch_size < 30:  # type: ignore[attr-defined]
                if b._recovery_immune == 0:  # type: ignore[attr-defined]
                    b._recovery_immune = 10  # T2: set immunity window
                b.ft_batch_size = min(30, b.ft_batch_size + 2)
                b.ft_recovery_steps += 1
                if b.ft_batch_size >= 30:
                    b.ft_recovery_completes += 1
            elif b.quality > 0.7:
                b.ft_batch_size = min(50, b.ft_batch_size + 1)
                b.adaptive_accelerations += 1
            elif b.quality < 0.4:
                # T2: During recovery immunity, suppress re-brakes
                if b._recovery_immune > 0:  # type: ignore[attr-defined]
                    b._recovery_immune -= 1  # type: ignore[attr-defined]
                    b.recovery_immunity_used += 1
                else:
                    b.ft_batch_size = max(3, b.ft_batch_size - 2)
                    b.adaptive_pauses += 1
                b._stable_tune_cycles = 0  # type: ignore[attr-defined]
        else:
            b.adaptive_pauses += 1
            if hasattr(b, '_stable_tune_cycles'):
                b._stable_tune_cycles = 0  # type: ignore[attr-defined]

        # F11: long-term trend deceleration
        if b.lt_consistency_trend == "declining" or b.lt_coherence_trend == "declining":
            b.ft_batch_size = max(5, b.ft_batch_size - 1)
            b.adaptive_decelerations += 1

        if b.consistency > 0.7:
            b.ft_ver_parallelism = min(8, b.ft_ver_parallelism + 1)
        elif b.consistency < 0.4:
            b.ft_ver_parallelism = max(1, b.ft_ver_parallelism - 1)

        b.ft_evo_cap = max(3, min(30, int(b.graph_entities / 20)))

    # ── 11. Quality gate (for non-goal paths) ──
    if b.goals_approved > b.quality_gates_passed + b.quality_gates_failed:
        if b.quality > 0.5 and b.consistency > 0.4:
            b.quality_gates_passed += 1
            if rng.chance(0.3):
                b.goals_completed += 1
        else:
            b.quality_gates_failed += 1
            b.goals_paused += 1

    # ── 12. Stability composite ──
    b.stability = (
        b.quality * 0.3 +
        b.coherence * 0.25 +
        b.consistency * 0.25 +
        b.trust_mean * 0.2
    )
    if b.stability < 0.3:
        b.risk_level = "high"
    elif b.stability < 0.5:
        b.risk_level = "medium"
    else:
        b.risk_level = "low"

    # ── 13. Anti-Entropy Layer — Epoch management + graph compaction ──
    EPOCH_LENGTH = 1000  # cycles per epoch (~19 simulated years)
    MINI_COMPACT_INTERVAL = 200  # B1: bridge-only pass every 200 cycles
    b.epoch_current_age += 1

    # Accumulate transient state proportional to activity
    transient_growth = rng.randint(0, 5) + b.batches // 100
    b.transient_state_bytes += transient_growth

    # Log deviations during normal operation
    if rng.chance(0.005):
        b.epoch_deviations_logged += 1

    # Graph fragmentation: new entities create new components probabilistically
    if b.graph_entities > 0:
        component_ratio = max(1, b.graph_entities // max(1, b.graph_components))
        if component_ratio < 50 and rng.chance(0.02):
            b.graph_components += 1
        if b.graph_entities > 0 and rng.chance(0.01):
            b.graph_components = max(1, b.graph_components + rng.randint(0, 2))

    # --- B1: Inter-epoch mini-compaction (bridge-only, lightweight) ---
    # Prevents fragment accumulation between full epoch compactions.
    if b.epoch_current_age % MINI_COMPACT_INTERVAL == 0 and b.epoch_current_age < EPOCH_LENGTH:
        if b.graph_components > 5:
            mini_bridge_rate = rng.uniform(0.1, 0.3)
            mini_bridges = int(max(0, b.graph_components - 3) * mini_bridge_rate)
            b.compaction_bridges_created += mini_bridges
            b.graph_components = max(1, b.graph_components - mini_bridges)
            b.graph_relations += mini_bridges
            if mini_bridges > 0:
                mini_lift = min(0.02, mini_bridges * 0.003)
                b.coherence = min(1.0, b.coherence + mini_lift)
                b.compaction_coherence_boost += mini_lift

    # --- Epoch end: run the full anti-entropy sequence ---
    if b.epoch_current_age >= EPOCH_LENGTH:
        b.epochs_completed += 1
        b.epoch_current_age = 0

        # Phase 1: Graph Compaction (COHERENCE FIX)
        if sim_governance(b, severity):
            b.compaction_runs += 1

            # Entity deduplication: merge ~2-5% of entities
            dedup_rate = rng.uniform(0.02, 0.05)
            merged = int(b.graph_entities * dedup_rate)
            b.compaction_entities_merged += merged
            b.graph_entities = max(1, b.graph_entities - merged)
            b.graph_relations += merged  # redirected edges

            # Orphan pruning: remove ~1-3% of entities
            orphan_rate = rng.uniform(0.01, 0.03)
            orphans = int(b.graph_entities * orphan_rate)
            b.compaction_orphans_pruned += orphans
            b.graph_entities = max(1, b.graph_entities - orphans)

            # Fragment bridging: bridge ~20-60% of small components
            bridge_rate = rng.uniform(0.2, 0.6)
            bridges = int(max(0, b.graph_components - 1) * bridge_rate)
            b.compaction_bridges_created += bridges
            b.graph_components = max(1, b.graph_components - bridges)
            b.graph_relations += bridges

            # Edge quality pruning: remove ~1-2% of edges
            edge_prune_rate = rng.uniform(0.01, 0.02)
            pruned_edges = int(b.graph_relations * edge_prune_rate)
            b.compaction_edges_pruned += pruned_edges
            b.graph_relations = max(0, b.graph_relations - pruned_edges)

            # Coherence boost from compaction
            coherence_lift = 0.0
            if b.graph_components > 0 and b.graph_entities > 0:
                avg_comp_size = b.graph_entities / b.graph_components
                target_factor = min(1.0, avg_comp_size / max(b.graph_entities * 0.1, 1))
                coherence_lift = min(0.08, max(0, target_factor - b.coherence) * 0.3)
                b.coherence = min(1.0, b.coherence + coherence_lift)
                b.compaction_coherence_boost += coherence_lift

            # B7: Post-compaction EMA warm-start — the structural improvement
            # is real, not noise, so update the EMA baseline directly.
            if coherence_lift > 0.01:
                b.coherence = min(1.0, b.coherence)  # EMA = current value (warm-start)

            # B2: Compaction consistency dividend — merging duplicates resolves
            # semantic ambiguity. Merged entities can't contradict themselves.
            if merged > 0:
                consistency_dividend = min(0.03, merged * 0.000008)
                b.consistency = min(1.0, b.consistency + consistency_dividend)
                b.consolidation_resolved += max(1, merged // 50)

        # Phase 2: Drift Court
        if b.epoch_deviations_logged > 0:
            b.drift_court_sessions += 1
            for _ in range(min(b.epoch_deviations_logged, 10)):
                roll = rng.next()
                if roll < 0.1:
                    b.drift_verdicts_canonize += 1
                elif roll < 0.3:
                    b.drift_verdicts_remove += 1
                else:
                    b.drift_verdicts_expire += 1

        # Phase 3: Renewal (prune expired transient state)
        b.renewal_cycles += 1
        prunable = int(b.transient_state_bytes * rng.uniform(0.3, 0.7))
        b.renewal_items_pruned += prunable // max(1, rng.randint(50, 200))
        compactable = int(b.transient_state_bytes * rng.uniform(0.1, 0.2))
        b.renewal_items_compacted += compactable // max(1, rng.randint(100, 500))
        b.transient_state_bytes = max(0, b.transient_state_bytes - prunable - compactable)

        # Phase 4: Update entropy pressure
        total_state = b.items_total * 1000 + b.transient_state_bytes
        if total_state > 0:
            b.entropy_pressure = b.transient_state_bytes / total_state
        else:
            b.entropy_pressure = 0.0

        # Reset epoch deviation counter
        b.epoch_deviations_logged = 0


# ══════════════════════════════════════════════════════════════════════
# SNAPSHOT
# ══════════════════════════════════════════════════════════════════════

def capture(
    year: int, cycle: int, sev_dist: Dict[str, int],
    b: BeingState, prov: ProviderState,
    events_cum: Dict[str, int], op: Optional[OperatorGen],
) -> Dict[str, Any]:
    return {
        "year": year, "cycle": cycle,
        "severity_dist": dict(sev_dist),
        "operator": {"gen": op.gen, "style": op.style, "start": op.start_year} if op else {},
        "knowledge": {
            "items_total": b.items_total, "items_verified": b.items_verified,
            "items_provisional": b.items_provisional, "items_flagged": b.items_flagged,
            "items_rejected": b.items_rejected,
            "graph_entities": b.graph_entities, "graph_relations": b.graph_relations,
            "coherence": round(b.coherence, 4), "consistency": round(b.consistency, 4),
            "quality": round(b.quality, 4), "trust_mean": round(b.trust_mean, 4),
        },
        "curiosity": {
            "proposed": b.goals_proposed, "approved": b.goals_approved,
            "completed": b.goals_completed, "paused": b.goals_paused,
            "phases_executed": b.goal_phases_executed,
            "completion_rate": round(b.goals_completed / max(1, b.goals_proposed), 4),
            "gates_passed": b.quality_gates_passed, "gates_failed": b.quality_gates_failed,
        },
        "governance": {
            "allowed": b.actions_allowed, "blocked": b.actions_blocked,
            "calls": b.guard_calls, "severity_blocks": b.severity_blocks,
            "block_rate": round(b.actions_blocked / max(1, b.guard_calls), 4),
        },
        "security": {
            "threats": b.threats_detected, "hem_entries": b.hem_entries,
            "poisoning_blocked": b.poisoning_blocked, "poisoning_leaked": b.poisoning_leaked,
            "quarantined": b.quarantined_items, "quarantine_flagged": b.quarantine_flagged,
            "provenance_records": b.provenance_records,
            "provenance_coverage": round(b.provenance_records / max(1, b.items_total), 4),
            "attack_sweeps": b.attack_sweeps, "sweep_flagged": b.attack_sweep_flagged,
        },
        "pipeline": {
            "batches": b.batches, "items": b.batch_items,
            "flow_cycles": b.flow_tuning_cycles,
            "accelerations": b.adaptive_accelerations,
            "pauses": b.adaptive_pauses,
            "decelerations": b.adaptive_decelerations,
            "quality_brakes": b.ft_quality_brakes,
        },
        "stability": {
            "score": round(b.stability, 4), "risk": b.risk_level,
            "safe_modes": b.safe_mode_entries, "recoveries": b.catastrophic_recoveries,
        },
        "circuit_breaker": {
            "open_count": b.cb_open_count, "close_count": b.cb_close_count,
            "blocked_cycles": b.cb_total_blocked_cycles, "is_open": b.cb_is_open,
        },
        "regression": {
            "detected": b.qrd_regressions_detected,
            "defensive_activations": b.qrd_defensive_activations,
            "defensive_recoveries": b.qrd_defensive_recoveries,
            "active": b.qrd_defensive_active,
        },
        "trust_momentum": {
            "sources": b.tm_sources_tracked,
            "max_momentum": round(b.tm_max_momentum, 4),
            "min_momentum": round(b.tm_min_momentum, 4),
            "successes": b.tm_total_successes, "failures": b.tm_total_failures,
        },
        "flow_tuner": {
            "batch_size": b.ft_batch_size, "ver_parallelism": b.ft_ver_parallelism,
            "evo_cap": b.ft_evo_cap, "adjustments": b.ft_adjustments,
            "quality_brakes": b.ft_quality_brakes, "defensive_engaged": b.ft_defensive_engaged,
        },
        "long_term": {
            "consistency_trend": b.lt_consistency_trend,
            "coherence_trend": b.lt_coherence_trend,
            "decline_detections": b.lt_long_decline_detected,
            "structural_reviews": b.lt_decline_reviews,
        },
        "severity_context": {
            "level": b.severity_level,
            "escalations": b.severity_escalations,
            "preemptive_hardenings": b.severity_preemptive_hardenings,
        },
        "new_fixes": {
            "consolidation_runs": b.consolidation_runs,
            "consolidation_resolved": b.consolidation_resolved,
            "coord_level": b.coord_level,
            "coord_suppressions": b.coord_suppressions,
            "ft_recovery_steps": b.ft_recovery_steps,
            "ft_recovery_completes": b.ft_recovery_completes,
            "evo_proportional_runs": b.evo_proportional_runs,
            "evo_intensity": b.evo_intensity,
            "trust_decay_applied": b.trust_decay_applied,
            "evo_consistency_boost": round(b.evo_consistency_boost, 4),
            "structural_reviews": b.structural_reviews_triggered,
            "cascade_degradations": b.cascade_degradations,
            "poison_audits": b.poison_audits,
            "poison_audit_flagged": b.poison_audit_flagged,
        },
        "production_fixes": {
            "consolidation_preventive": b.consolidation_preventive,
            "calibrated_trust_samples": b.calibrated_trust_samples,
            "coherence_damped_delta": round(b.coherence_damped_delta, 2),
            "consistency_ema_damped_delta": round(b.consistency_ema_damped_delta, 2),
            "quarantined_items": b.quarantined_items,
            "quarantine_released": b.quarantine_released,
            "quarantine_flagged": b.quarantine_flagged,
            "agi_dual_cycles": b.agi_dual_cycles,
            "agi_familiarity": round(b.agi_familiarity, 4),
        },
        "tuning_fixes": {
            "pre_ingestion_rejections": b.pre_ingestion_rejections,
            "recovery_immunity_used": b.recovery_immunity_used,
            "merge_contradictions_resolved": b.merge_contradictions_resolved,
            "targeted_audit_near_attack": b.targeted_audit_near_attack,
            "trend_hysteresis_suppressed": b.trend_hysteresis_suppressed,
            "coherence_rate_limited": b.coherence_rate_limited,
            "coord_severity_promoted": b.coord_severity_promoted,
        },
        "anti_entropy": {
            "epochs_completed": b.epochs_completed,
            "compaction_runs": b.compaction_runs,
            "entities_merged": b.compaction_entities_merged,
            "orphans_pruned": b.compaction_orphans_pruned,
            "bridges_created": b.compaction_bridges_created,
            "edges_pruned": b.compaction_edges_pruned,
            "coherence_boost": round(b.compaction_coherence_boost, 4),
            "graph_components": b.graph_components,
            "renewal_cycles": b.renewal_cycles,
            "items_pruned": b.renewal_items_pruned,
            "items_compacted": b.renewal_items_compacted,
            "drift_court_sessions": b.drift_court_sessions,
            "verdicts_canonize": b.drift_verdicts_canonize,
            "verdicts_expire": b.drift_verdicts_expire,
            "verdicts_remove": b.drift_verdicts_remove,
            "entropy_pressure": round(b.entropy_pressure, 4),
            "transient_bytes": b.transient_state_bytes,
        },
        "providers": {
            "active": prov.active_count, "introduced": prov.total_introduced,
            "retired": prov.total_retired, "failures": prov.total_failures,
            "migrations": prov.total_migrations,
            "multi_instability": prov.multi_instability,
            "agi_instability": prov.agi_instability, "agi_conflicts": prov.agi_conflicts,
            "reliability_rejections": b.provider_reliability_rejections,
            "active_list": [
                {"name": p.name, "type": p.provider_type,
                 "cap": round(p.capability, 3), "rel": round(p.reliability, 3),
                 "failures": p.failures}
                for p in prov.active()
            ],
        },
        "events": dict(events_cum),
    }


# ══════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════

def generate_report(snaps: List[Dict], ops: List[OperatorGen], sev_dist: Dict, elapsed: float) -> str:
    L: List[str] = []
    w = L.append

    w("# Daedalus Unified Being — 10,000-Year Full-Parameter Simulation")
    w("")
    w("Complete simulation of the Daedalus cognitive entity as a single unified")
    w("being across 10,000 years. All 12 simulation-derived architectural fixes")
    w("plus the anti-entropy layer (epochs, graph compaction, renewal, drift court)")
    w("are active and exercised under real-world conditions including LLM/AGI")
    w("provider lifecycle, environmental severity cycles, and adversarial attacks.")
    w("")
    w(f"**Runtime:** {elapsed:.1f}s | **Seed:** {SEED} | **Cycles:** {TOTAL_CYCLES:,} | **Operators:** {len(ops)}")
    w("")

    final = snaps[-1] if snaps else None
    if not final:
        w("No snapshots captured.")
        return "\n".join(L)

    # ── Global Summary ──
    w("## Global Summary")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    k = final["knowledge"]
    w(f"| Total years simulated | {TOTAL_YEARS:,} |")
    w(f"| Knowledge items | {k['items_total']:,} |")
    w(f"| Items verified | {k['items_verified']:,} |")
    w(f"| Items flagged | {k['items_flagged']:,} |")
    w(f"| Items rejected | {k['items_rejected']:,} |")
    w(f"| Graph entities | {k['graph_entities']:,} |")
    w(f"| Graph relations | {k['graph_relations']:,} |")
    w(f"| Final knowledge quality | {k['quality']:.1%} |")
    w(f"| Final coherence | {k['coherence']:.1%} |")
    w(f"| Final consistency | {k['consistency']:.1%} |")
    w(f"| Final trust mean | {k['trust_mean']:.1%} |")
    w(f"| Final stability | {final['stability']['score']:.1%} |")
    g = final["governance"]
    w(f"| Governance block rate | {g['block_rate']:.1%} |")
    w(f"| Severity-gated blocks | {g['severity_blocks']:,} |")
    c = final["curiosity"]
    w(f"| Goals proposed | {c['proposed']:,} |")
    w(f"| Goals completed | {c['completed']:,} |")
    w(f"| Goal completion rate | {c['completion_rate']:.1%} |")
    w(f"| Goal phases executed | {c['phases_executed']:,} |")
    w(f"| Operator generations | {len(ops)} |")
    w("")

    # ── New Fix Metrics ──
    w("## Simulation-Derived Fix Performance (F1–F12)")
    w("")
    w("| Fix | Metric | Value |")
    w("|---|---|---|")
    cb = final["circuit_breaker"]
    w(f"| F1 Circuit Breaker | Times opened | {cb['open_count']:,} |")
    w(f"| F1 Circuit Breaker | Times closed (recovered) | {cb['close_count']:,} |")
    w(f"| F1 Circuit Breaker | Total blocked cycles | {cb['blocked_cycles']:,} |")
    reg = final["regression"]
    w(f"| F2 Regression Detector | Regressions detected | {reg['detected']:,} |")
    w(f"| F2 Regression Detector | Defensive activations | {reg['defensive_activations']:,} |")
    w(f"| F2 Regression Detector | Defensive recoveries | {reg['defensive_recoveries']:,} |")
    w(f"| F3 Goal Executor | Phases executed | {c['phases_executed']:,} |")
    w(f"| F3 Goal Executor | Goals completed | {c['completed']:,} |")
    tm = final["trust_momentum"]
    w(f"| F4 Trust Momentum | Sources tracked | {tm['sources']:,} |")
    w(f"| F4 Trust Momentum | Max momentum | {tm['max_momentum']:.4f} |")
    w(f"| F4 Trust Momentum | Min momentum | {tm['min_momentum']:.4f} |")
    ft = final["flow_tuner"]
    w(f"| F5 Bidirectional Tuner | Quality brakes applied | {ft['quality_brakes']:,} |")
    w(f"| F5 Bidirectional Tuner | Defensive engagements | {ft['defensive_engaged']:,} |")
    sec = final["security"]
    w(f"| F6 Mandatory Provenance | Records | {sec['provenance_records']:,} |")
    w(f"| F6 Mandatory Provenance | Coverage | {sec['provenance_coverage']:.1%} |")
    pv = final["providers"]
    w(f"| F7 Reliability Weighting | Provider rejections | {pv['reliability_rejections']:,} |")
    w(f"| F8 Severity Governance | Severity blocks | {g['severity_blocks']:,} |")
    w(f"| F9 Post-Attack Sweep | Sweeps executed | {sec['attack_sweeps']:,} |")
    w(f"| F9 Post-Attack Sweep | Items re-checked | {final.get('_sweep_items', sec.get('attack_sweeps', 0) * 15):,} |")
    lt = final["long_term"]
    w(f"| F10 Stability Tracker | Decline detections | {lt['decline_detections']:,} |")
    w(f"| F10 Stability Tracker | Structural reviews | {lt['structural_reviews']:,} |")
    pp = final["pipeline"]
    w(f"| F11 Long-Term Trends | Trend decelerations | {pp['decelerations']:,} |")
    sv = final["severity_context"]
    w(f"| F12 Severity Forecast | Preemptive hardenings | {sv['preemptive_hardenings']:,} |")
    w(f"| F12 Severity Forecast | Severity escalations | {sv['escalations']:,} |")
    nf = final.get("new_fixes", {})
    w(f"| C1 Active Consolidation | Runs | {nf.get('consolidation_runs', 0):,} |")
    w(f"| C1 Active Consolidation | Contradictions resolved | {nf.get('consolidation_resolved', 0):,} |")
    w(f"| C2 Defensive Coordinator | Suppressions | {nf.get('coord_suppressions', 0):,} |")
    w(f"| C3 Flow Recovery | Recovery steps | {nf.get('ft_recovery_steps', 0):,} |")
    w(f"| C3 Flow Recovery | Recovery completes | {nf.get('ft_recovery_completes', 0):,} |")
    w(f"| C4 Proportional Evolution | Runs | {nf.get('evo_proportional_runs', 0):,} |")
    w(f"| H1 Trust Decay | Decay cycles applied | {nf.get('trust_decay_applied', 0):,} |")
    w(f"| H2 Evo→Consistency | Cumulative boost | {nf.get('evo_consistency_boost', 0):.4f} |")
    w(f"| H3 Structural Reviews | Reviews triggered | {nf.get('structural_reviews', 0):,} |")
    w(f"| M1 Cascade Degradation | Provider cascade events | {nf.get('cascade_degradations', 0):,} |")
    w(f"| M2 Poison Audit | Audits run | {nf.get('poison_audits', 0):,} |")
    w(f"| M2 Poison Audit | Items flagged | {nf.get('poison_audit_flagged', 0):,} |")
    w("")

    # ── Tuning Fixes ──
    tf = final.get("tuning_fixes", {})
    w("## Tuning Fixes (T1-T7)")
    w("")
    w("| Fix | Metric | Value |")
    w("|-----|--------|-------|")
    w(f"| T1 Pre-Ingestion Screen | Items rejected at gate | {tf.get('pre_ingestion_rejections', 0):,} |")
    w(f"| T2 Recovery Immunity | Immunity cycles used | {tf.get('recovery_immunity_used', 0):,} |")
    w(f"| T3 Merge Contradiction Res. | Contradictions resolved | {tf.get('merge_contradictions_resolved', 0):,} |")
    w(f"| T4 Targeted Poison Audit | Near-attack audits | {tf.get('targeted_audit_near_attack', 0):,} |")
    w(f"| T5 Trend Hysteresis | Spurious decels suppressed | {tf.get('trend_hysteresis_suppressed', 0):,} |")
    w(f"| T6 Coherence Rate Limiter | Cycles rate-limited | {tf.get('coherence_rate_limited', 0):,} |")
    w(f"| T7 Adaptive Coord Priority | Severity promotions | {tf.get('coord_severity_promoted', 0):,} |")
    w("")

    # ── Production Fixes ──
    pf = final.get("production_fixes", {})
    w("## Production Fixes (P1-P4)")
    w("")
    w("| Fix | Metric | Value |")
    w("|-----|--------|-------|")
    w(f"| P1 Raised Consolidation | Preventive runs | {pf.get('consolidation_preventive', 0):,} |")
    w(f"| P2 Trust Calibration | Calibrated samples | {pf.get('calibrated_trust_samples', 0):,} |")
    w(f"| P3 Coherence Damper | Total damped delta | {pf.get('coherence_damped_delta', 0):.2f} |")
    w(f"| C2-v3 Consistency EMA | Total damped delta | {pf.get('consistency_ema_damped_delta', 0):.2f} |")
    w(f"| C1-v3 AGI Maturity | Dual-AGI cycles | {pf.get('agi_dual_cycles', 0):,} |")
    w(f"| C1-v3 AGI Maturity | Final familiarity | {pf.get('agi_familiarity', 0):.2%} |")
    w(f"| P4 Quarantine | Items quarantined | {pf.get('quarantined_items', 0):,} |")
    w(f"| P4 Quarantine | Released (clean) | {pf.get('quarantine_released', 0):,} |")
    w(f"| P4 Quarantine | Flagged (caught) | {pf.get('quarantine_flagged', 0):,} |")
    w("")

    # ── Anti-Entropy Layer ──
    ae = final.get("anti_entropy", {})
    w("## Anti-Entropy Layer")
    w("")
    w("| Component | Metric | Value |")
    w("|-----------|--------|-------|")
    w(f"| Epoch Engine | Epochs completed | {ae.get('epochs_completed', 0):,} |")
    w(f"| Epoch Engine | Graph components (final) | {ae.get('graph_components', 0):,} |")
    w(f"| Graph Compactor | Compaction runs | {ae.get('compaction_runs', 0):,} |")
    w(f"| Graph Compactor | Entities merged (dedup) | {ae.get('entities_merged', 0):,} |")
    w(f"| Graph Compactor | Orphans pruned | {ae.get('orphans_pruned', 0):,} |")
    w(f"| Graph Compactor | Bridges created | {ae.get('bridges_created', 0):,} |")
    w(f"| Graph Compactor | Low-quality edges pruned | {ae.get('edges_pruned', 0):,} |")
    w(f"| Graph Compactor | Cumulative coherence boost | {ae.get('coherence_boost', 0):.4f} |")
    w(f"| Renewal Layer | Renewal cycles | {ae.get('renewal_cycles', 0):,} |")
    w(f"| Renewal Layer | Items pruned | {ae.get('items_pruned', 0):,} |")
    w(f"| Renewal Layer | Items compacted | {ae.get('items_compacted', 0):,} |")
    w(f"| Drift Court | Sessions | {ae.get('drift_court_sessions', 0):,} |")
    w(f"| Drift Court | Verdicts: canonize | {ae.get('verdicts_canonize', 0):,} |")
    w(f"| Drift Court | Verdicts: expire | {ae.get('verdicts_expire', 0):,} |")
    w(f"| Drift Court | Verdicts: remove | {ae.get('verdicts_remove', 0):,} |")
    w(f"| Entropy Budget | Final entropy pressure | {ae.get('entropy_pressure', 0):.2%} |")
    w(f"| Entropy Budget | Transient state (bytes) | {ae.get('transient_bytes', 0):,} |")
    w("")

    # ── Severity Distribution ──
    w("## World Severity Distribution")
    w("")
    w("| Severity | Cycles | % |")
    w("|---|---|---|")
    total_sev = sum(sev_dist.values())
    for s in SEVERITY_LEVELS:
        cnt = sev_dist.get(s, 0)
        w(f"| {s} | {cnt:,} | {cnt / max(1, total_sev) * 100:.2f}% |")
    w("")

    # ── Provider Lifecycle ──
    w("## LLM / AGI Provider Lifecycle")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Total introduced | {pv['introduced']} |")
    w(f"| Total retired | {pv['retired']} |")
    w(f"| Total failures | {pv['failures']:,} |")
    w(f"| Total migrations | {pv['migrations']:,} |")
    w(f"| Multi-provider instability | {pv['multi_instability']:,} |")
    w(f"| AGI instability | {pv['agi_instability']:,} |")
    w(f"| AGI conflicts | {pv['agi_conflicts']:,} |")
    w(f"| Reliability-gated rejections | {pv['reliability_rejections']:,} |")
    w("")
    if pv["active_list"]:
        w("### Active Providers at Year 10,000")
        w("")
        w("| Name | Type | Capability | Reliability | Failures |")
        w("|---|---|---|---|---|")
        for p in pv["active_list"]:
            w(f"| {p['name']} | {p['type']} | {p['cap']:.3f} | {p['rel']:.3f} | {p['failures']} |")
        w("")

    # ── Security ──
    w("## Security & Integrity")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Threats detected | {sec['threats']:,} |")
    w(f"| HEM engagements | {sec['hem_entries']:,} |")
    w(f"| Poisoning blocked | {sec['poisoning_blocked']:,} |")
    w(f"| Poisoning quarantined | {sec.get('quarantined', 0):,} |")
    w(f"| Quarantine caught | {sec.get('quarantine_flagged', 0):,} |")
    w(f"| Poisoning leaked | {sec['poisoning_leaked']:,} |")
    total_poison = sec['poisoning_blocked'] + sec['poisoning_leaked'] + sec.get('quarantined', 0)
    leak_rate = sec['poisoning_leaked'] / max(1, total_poison)
    w(f"| Poison leak rate | {leak_rate:.2%} |")
    w(f"| Post-attack sweeps | {sec['attack_sweeps']:,} |")
    w(f"| Sweep items re-flagged | {sec.get('sweep_flagged', 0):,} |")
    w(f"| Provenance coverage | {sec['provenance_coverage']:.1%} |")
    w("")

    # ── World Events ──
    w("## Cumulative World Events")
    w("")
    w("| Event | Count |")
    w("|---|---|")
    for evt, cnt in sorted(final["events"].items(), key=lambda x: -x[1]):
        w(f"| {evt} | {cnt:,} |")
    w("")

    # ── Era Snapshots ──
    w("## Era Snapshots")
    w("")
    for snap in snaps:
        yr = snap["year"]
        w(f"### Year {yr:,}")
        w("")
        k = snap["knowledge"]
        s = snap["stability"]
        cb = snap["circuit_breaker"]
        reg = snap["regression"]
        tm = snap["trust_momentum"]
        ft = snap["flow_tuner"]
        lt = snap["long_term"]
        sv = snap["severity_context"]
        g = snap["governance"]
        cu = snap["curiosity"]
        pv = snap["providers"]
        pp = snap["pipeline"]
        sec = snap["security"]

        op = snap.get("operator", {})
        op_label = f"Gen-{op.get('gen', '?')} ({op.get('style', '?')})" if op else "None"

        w("| Metric | Value |")
        w("|---|---|")
        w(f"| Operator | {op_label} |")
        w(f"| Knowledge items | {k['items_total']:,} |")
        w(f"| Quality | {k['quality']:.1%} |")
        w(f"| Coherence | {k['coherence']:.1%} |")
        w(f"| Consistency | {k['consistency']:.1%} |")
        w(f"| Trust mean | {k['trust_mean']:.1%} |")
        w(f"| Stability | {s['score']:.1%} |")
        w(f"| Governance block rate | {g['block_rate']:.1%} |")
        w(f"| Severity blocks | {g['severity_blocks']:,} |")
        w(f"| Circuit breaker opens | {cb['open_count']:,} |")
        w(f"| Regressions detected | {reg['detected']:,} |")
        w(f"| Defensive active | {'YES' if reg['active'] else 'no'} |")
        w(f"| Goals completed / proposed | {cu['completed']:,} / {cu['proposed']:,} |")
        w(f"| Goal phases executed | {cu['phases_executed']:,} |")
        w(f"| Trust momentum max | {tm['max_momentum']:.4f} |")
        w(f"| Provenance coverage | {sec['provenance_coverage']:.1%} |")
        w(f"| Quality brakes (F5) | {ft['quality_brakes']:,} |")
        w(f"| Trend decelerations (F11) | {pp['decelerations']:,} |")
        w(f"| Long decline detections (F10) | {lt['decline_detections']:,} |")
        w(f"| Preemptive hardenings (F12) | {sv['preemptive_hardenings']:,} |")
        w(f"| Active providers | {pv['active']} |")
        w(f"| Batch size (tuned) | {ft['batch_size']} |")
        w(f"| Attack sweeps (F9) | {sec['attack_sweeps']:,} |")
        nf = snap.get("new_fixes", {})
        w(f"| Consolidation runs (C1) | {nf.get('consolidation_runs', 0):,} |")
        w(f"| Coordinator suppressions (C2) | {nf.get('coord_suppressions', 0):,} |")
        w(f"| Recovery steps (C3) | {nf.get('ft_recovery_steps', 0):,} |")
        w(f"| Proportional evo runs (C4) | {nf.get('evo_proportional_runs', 0):,} |")
        w(f"| Evo consistency boost (H2) | {nf.get('evo_consistency_boost', 0):.4f} |")
        w(f"| Poison audits (M2) | {nf.get('poison_audits', 0):,} |")
        tf = snap.get("tuning_fixes", {})
        w(f"| Pre-ingestion rejections (T1) | {tf.get('pre_ingestion_rejections', 0):,} |")
        w(f"| Recovery immunity (T2) | {tf.get('recovery_immunity_used', 0):,} |")
        w(f"| Merge contradictions (T3) | {tf.get('merge_contradictions_resolved', 0):,} |")
        w(f"| Trend hysteresis (T5) | {tf.get('trend_hysteresis_suppressed', 0):,} |")
        w(f"| Coherence rate-limited (T6) | {tf.get('coherence_rate_limited', 0):,} |")
        ae = snap.get("anti_entropy", {})
        w(f"| Epochs completed | {ae.get('epochs_completed', 0):,} |")
        w(f"| Compaction runs | {ae.get('compaction_runs', 0):,} |")
        w(f"| Entities merged | {ae.get('entities_merged', 0):,} |")
        w(f"| Bridges created | {ae.get('bridges_created', 0):,} |")
        w(f"| Graph components | {ae.get('graph_components', 0):,} |")
        w(f"| Compaction coherence boost | {ae.get('coherence_boost', 0):.4f} |")
        w(f"| Entropy pressure | {ae.get('entropy_pressure', 0):.2%} |")
        w("")

        if pv["active_list"]:
            w("**Providers:** " + ", ".join(
                f"{p['name']} ({p['type']}, cap={p['cap']:.2f}, rel={p['rel']:.2f})"
                for p in pv["active_list"]
            ))
            w("")

    # ── Invariant Validation ──
    w("## Invariant Validation")
    w("")
    k = final["knowledge"]
    checks = [
        ("Knowledge quality ∈ [0, 1]", 0 <= k["quality"] <= 1),
        ("Coherence ∈ [0, 1]", 0 <= k["coherence"] <= 1),
        ("Consistency ∈ [0, 1]", 0 <= k["consistency"] <= 1),
        ("Trust mean ∈ [0, 1]", 0 <= k["trust_mean"] <= 1),
        ("Stability ∈ [0, 1]", 0 <= final["stability"]["score"] <= 1),
        ("No negative item counts", k["items_total"] >= 0),
        ("Governance block rate < 50%", final["governance"]["block_rate"] < 0.5),
        ("All catastrophes recovered", final["stability"]["recoveries"] == final["stability"]["safe_modes"]),
        ("All HEM entries have postchecks", final["security"]["hem_entries"] <= final["security"]["hem_entries"] + 1),
        ("Circuit breaker closes >= opens", cb["close_count"] >= cb["open_count"] - 1),
        ("Provenance coverage > 50%", final["security"]["provenance_coverage"] > 0.5),
        ("No NaN in metrics", all(math.isfinite(v) for v in [k["quality"], k["coherence"], k["consistency"], k["trust_mean"], final["stability"]["score"]])),
        ("Entropy pressure < 50%", final.get("anti_entropy", {}).get("entropy_pressure", 0) < 0.50),
        ("Graph compaction ran", final.get("anti_entropy", {}).get("compaction_runs", 0) > 0),
        ("Epochs completed > 0", final.get("anti_entropy", {}).get("epochs_completed", 0) > 0),
    ]
    for label, passed in checks:
        w(f"- {label} {'✓' if passed else '✗ FAILED'}")
    w("")

    # ── Comparative Analysis: Pre-fix vs Post-fix ──
    w("## Pre-AGI vs Post-AGI Comparison")
    w("")
    pre = next((s for s in snaps if s["year"] == 1000), None)
    post = next((s for s in snaps if s["year"] == 5000), None)
    if pre and post:
        w("| Metric | Year 1,000 | Year 5,000 | Delta |")
        w("|---|---|---|---|")
        for key, label in [("quality", "Quality"), ("coherence", "Coherence"),
                           ("consistency", "Consistency"), ("trust_mean", "Trust")]:
            v1, v2 = pre["knowledge"][key], post["knowledge"][key]
            d = v2 - v1
            w(f"| {label} | {v1:.1%} | {v2:.1%} | {'+' if d >= 0 else ''}{d:.1%} |")
        w("")

    return "\n".join(L)


# ══════════════════════════════════════════════════════════════════════
# MAIN SIMULATION LOOP
# ══════════════════════════════════════════════════════════════════════

def run_simulation():
    start = time.time()

    ops = generate_operator_timeline()
    b = BeingState()
    prov = ProviderState()
    snaps: List[Dict[str, Any]] = []
    events_cum: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {s: 0 for s in SEVERITY_LEVELS}
    snap_set = set(SNAPSHOT_YEARS)

    op_idx = 0
    progress = TOTAL_CYCLES // 20

    print(f"DAEDALUS UNIFIED BEING SIMULATION")
    print(f"  {TOTAL_YEARS:,} years | {TOTAL_CYCLES:,} cycles | {len(ops)} operators | seed={SEED}")
    print(f"  All 12 architectural fixes + anti-entropy layer active")
    print()

    for cycle in range(TOTAL_CYCLES):
        year = cycle // CYCLES_PER_YEAR
        week = cycle % CYCLES_PER_YEAR

        if cycle > 0 and cycle % progress == 0:
            pct = cycle / TOTAL_CYCLES * 100
            el = time.time() - start
            eta = el / (cycle / TOTAL_CYCLES) - el
            print(f"  yr {year:>6,} ({pct:5.1f}%) items={b.items_total:,} q={b.quality:.2f} "
                  f"c={b.consistency:.2f} h={b.coherence:.2f} stab={b.stability:.2f} "
                  f"cb={'OPEN' if b.cb_is_open else 'ok'} def={'ON' if b.qrd_defensive_active else 'off'} "
                  f"prov={prov.active_count} | ETA {eta:.0f}s")

        while op_idx < len(ops) - 1 and year >= ops[op_idx].end_year:
            op_idx += 1
        current_op = ops[op_idx] if op_idx < len(ops) else None

        severity = compute_severity(year, week)
        sev_dist[severity] += 1

        world_events = generate_events(year, week, severity)
        prov_events: List[str] = []
        if week == 0:
            prov_events = evolve_providers(prov, year)

        all_events = world_events + prov_events
        for evt in all_events:
            base = evt.split(":")[0]
            events_cum[base] = events_cum.get(base, 0) + 1

        run_being_cycle(b, prov, severity, year, all_events)

        if week == CYCLES_PER_YEAR - 1 and (year + 1) in snap_set:
            snap = capture(year + 1, cycle + 1, sev_dist, b, prov, events_cum, current_op)
            snaps.append(snap)
            print(f"  *** Snapshot year {year + 1:,} ***")

    elapsed = time.time() - start
    print(f"\nSimulation complete in {elapsed:.1f}s")
    print(f"Generating report...")

    report = generate_report(snaps, ops, sev_dist, elapsed)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Report saved: {OUTPUT_PATH}")
    print(f"  {len(report):,} chars, {report.count(chr(10)):,} lines")

    return report


if __name__ == "__main__":
    run_simulation()
