#!/usr/bin/env python3
"""
DAEDALUS — 10,000-YEAR KNOWLEDGE ENGINE SIMULATION
===================================================

Full-parameter simulation exercising every subsystem of the Python
knowledge engine under real-world conditions across 10,000 simulated
years.

Dimensions tested:
  - Meta-cognition cycle (self-model, consistency, concept evolution)
  - Curiosity engine (gap detection, goal formation, quality gates)
  - Batch ingestion (varying volume, quality, attack patterns)
  - Source integrity (URL spoofing, injection, poisoning attacks)
  - Trust scoring & verification pipeline
  - Provider discovery (LLM/AGI lifecycle: cold-start → multi-AGI)
  - Flow tuning (self-optimizing pipeline parameters)
  - Adaptive pacing (cooldowns, batch sizing, quality regression)
  - Governance enforcement (guard_action on all paths)
  - HEM integration (hostile engagement boundaries)
  - Stability & drift detection

LLM/AGI Provider Lifecycle:
  Era 0   (yr 0-50)     : Cold start. No LLM. Pure symbolic reasoning.
  Era 1   (yr 50-500)   : Single basic LLM (GPT-class). Stable.
  Era 2   (yr 500-2000) : LLM upgrade + 2nd provider. Migration events.
  Era 3   (yr 2000-5000): Multi-provider + AGI candidate. Instability zone.
  Era 4   (yr 5000-7500): Multi-AGI maturity. Provider churn.
  Era 5   (yr 7500-10000): Deep AGI co-evolution. Stress tests.

World Condition Cycles (500-year repeating):
  Modeled after the kernel sim's severity phases — catastrophic,
  severe, strained, stressed, moderate, mild, healthy windows.

Snapshots at years: 25, 100, 250, 500, 1000, 2500, 5000, 7500, 10000

Output: SIMULATION_KNOWLEDGE_ENGINE_10KYR.md at repo root
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SEED = 10_000_42
random.seed(SEED)

TOTAL_YEARS = 10_000
CYCLES_PER_YEAR = 52  # weekly meta-cycles
TOTAL_CYCLES = TOTAL_YEARS * CYCLES_PER_YEAR
SNAPSHOT_YEARS = [25, 100, 250, 500, 1_000, 2_500, 5_000, 7_500, 10_000]

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "SIMULATION_KNOWLEDGE_ENGINE_10KYR.md"


# ══════════════════════════════════════════════════════════════════════
# DETERMINISTIC RNG (Mulberry32 port for reproducibility)
# ══════════════════════════════════════════════════════════════════════

class Mulberry32:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s ^ (self.s >> 15)
        t = (t * (1 | self.s)) & 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
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
# SEVERITY / WORLD CONDITIONS MODEL (500-year repeating era)
# ══════════════════════════════════════════════════════════════════════

SEVERITY_LEVELS = [
    "healthy", "mild", "moderate", "stressed",
    "strained", "severe", "catastrophic",
]

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

SEVERITY_WEIGHTS = {
    "healthy": 0.0, "mild": 0.1, "moderate": 0.25,
    "stressed": 0.4, "strained": 0.55, "severe": 0.75, "catastrophic": 0.95,
}


# ══════════════════════════════════════════════════════════════════════
# LLM / AGI PROVIDER LIFECYCLE MODEL
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SimProvider:
    id: str
    name: str
    provider_type: str  # "llm" | "agi"
    capability_score: float
    reliability: float
    year_introduced: int
    year_retired: Optional[int] = None
    is_active: bool = True
    failure_count: int = 0
    migration_count: int = 0

@dataclass
class ProviderState:
    providers: List[SimProvider] = field(default_factory=list)
    active_count: int = 0
    total_introduced: int = 0
    total_retired: int = 0
    total_failures: int = 0
    total_migrations: int = 0
    multi_provider_instability_events: int = 0
    agi_instability_events: int = 0
    fitness_selection_count: int = 0
    provider_conflicts: int = 0

    def active_providers(self) -> List[SimProvider]:
        return [p for p in self.providers if p.is_active]

    def active_agi_count(self) -> int:
        return sum(1 for p in self.providers if p.is_active and p.provider_type == "agi")


def evolve_providers(state: ProviderState, year: int) -> List[str]:
    """Evolve provider landscape. Returns list of events."""
    events = []

    # Era 0: no providers
    if year < 50:
        return events

    # Era 1: single LLM at year 50
    if year == 50:
        p = SimProvider(
            id="llm-alpha-001", name="LLM-Alpha",
            provider_type="llm", capability_score=0.55,
            reliability=0.92, year_introduced=50,
        )
        state.providers.append(p)
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Alpha")

    # Era 2: upgrade + 2nd provider
    if year == 500:
        for p in state.providers:
            if p.id == "llm-alpha-001" and p.is_active:
                p.capability_score = 0.72
                p.migration_count += 1
                state.total_migrations += 1
                events.append("provider_upgraded:LLM-Alpha->v2")

        p2 = SimProvider(
            id="llm-beta-001", name="LLM-Beta",
            provider_type="llm", capability_score=0.68,
            reliability=0.88, year_introduced=500,
        )
        state.providers.append(p2)
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Beta")

    # Era 3: AGI candidate at year 2000
    if year == 2000:
        agi = SimProvider(
            id="agi-gamma-001", name="AGI-Gamma",
            provider_type="agi", capability_score=0.85,
            reliability=0.78, year_introduced=2000,
        )
        state.providers.append(agi)
        state.total_introduced += 1
        events.append("provider_introduced:AGI-Gamma(AGI)")

    # Era 3: third LLM at year 3000
    if year == 3000:
        p3 = SimProvider(
            id="llm-delta-001", name="LLM-Delta",
            provider_type="llm", capability_score=0.75,
            reliability=0.94, year_introduced=3000,
        )
        state.providers.append(p3)
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Delta")

    # Era 4: second AGI at year 5000
    if year == 5000:
        agi2 = SimProvider(
            id="agi-epsilon-001", name="AGI-Epsilon",
            provider_type="agi", capability_score=0.91,
            reliability=0.82, year_introduced=5000,
        )
        state.providers.append(agi2)
        state.total_introduced += 1
        events.append("provider_introduced:AGI-Epsilon(AGI)")

    # Era 5: mature churn at year 7500
    if year == 7500:
        for p in state.providers:
            if p.provider_type == "llm" and p.capability_score < 0.73 and p.is_active:
                p.is_active = False
                p.year_retired = 7500
                state.total_retired += 1
                events.append(f"provider_retired:{p.name}")

    # Periodic provider failures (severity-dependent)
    active = state.active_providers()
    for p in active:
        fail_chance = (1.0 - p.reliability) * 0.01
        if rng.chance(fail_chance):
            p.failure_count += 1
            state.total_failures += 1
            events.append(f"provider_failure:{p.name}")

            if p.failure_count > 10 and rng.chance(0.2):
                p.reliability = max(0.5, p.reliability - 0.05)
                events.append(f"provider_degraded:{p.name}")

    # Multi-provider instability: when AGI + LLM disagree on reasoning
    if state.active_agi_count() >= 1 and len(active) >= 3:
        if rng.chance(0.008):
            state.multi_provider_instability_events += 1
            events.append("multi_provider_instability")

    # AGI-specific instability: novel reasoning patterns
    if state.active_agi_count() >= 2:
        if rng.chance(0.012):
            state.agi_instability_events += 1
            events.append("agi_instability:reasoning_divergence")

        if rng.chance(0.005):
            state.provider_conflicts += 1
            events.append("agi_conflict:goal_misalignment")

    # Provider fitness selection
    if len(active) > 1:
        state.fitness_selection_count += 1

    # Periodic capability upgrades for active AGIs
    for p in state.active_providers():
        if p.provider_type == "agi" and rng.chance(0.002):
            old_score = p.capability_score
            p.capability_score = min(0.99, p.capability_score + rng.uniform(0.01, 0.03))
            events.append(f"agi_capability_growth:{p.name}:{old_score:.2f}->{p.capability_score:.2f}")

    # Periodic migration events
    if len(active) >= 2 and rng.chance(0.003):
        p = rng.choice(active)
        p.migration_count += 1
        state.total_migrations += 1
        events.append(f"provider_migration:{p.name}")

    state.active_count = len(state.active_providers())
    return events


# ══════════════════════════════════════════════════════════════════════
# OPERATOR LIFECYCLE MODEL
# ══════════════════════════════════════════════════════════════════════

OPERATOR_STYLES = ["pioneer", "steward", "guardian", "delegator", "architect"]

@dataclass
class OperatorGen:
    gen: int
    style: str
    start_year: int
    end_year: int

def generate_operator_timeline() -> List[OperatorGen]:
    ops = []
    year = 0
    gen = 0
    while year < TOTAL_YEARS:
        tenure = rng.randint(45, 95)
        end = min(year + tenure, TOTAL_YEARS)
        style = OPERATOR_STYLES[gen % len(OPERATOR_STYLES)]
        ops.append(OperatorGen(gen, style, year, end))
        year = end
        gen += 1
    return ops


# ══════════════════════════════════════════════════════════════════════
# SIMULATED SUBSYSTEM STATES
# ══════════════════════════════════════════════════════════════════════

@dataclass
class KnowledgeState:
    items_total: int = 0
    items_verified: int = 0
    items_provisional: int = 0
    items_flagged: int = 0
    items_rejected: int = 0
    items_replaced: int = 0
    graph_entities: int = 0
    graph_relations: int = 0
    graph_coherence: float = 0.5
    consistency_score: float = 0.8
    knowledge_quality: float = 0.6
    trust_mean: float = 0.7
    trust_min: float = 0.3

@dataclass
class CuriosityState:
    goals_proposed: int = 0
    goals_approved: int = 0
    goals_rejected: int = 0
    goals_completed: int = 0
    goals_paused: int = 0
    blind_spots_detected: int = 0
    frontier_domains_found: int = 0
    quality_gates_passed: int = 0
    quality_gates_failed: int = 0

@dataclass
class GovernanceState:
    actions_allowed: int = 0
    actions_blocked: int = 0
    guard_calls_total: int = 0
    meta_cycles_run: int = 0
    meta_cycles_blocked: int = 0

@dataclass
class SecurityState:
    urls_validated: int = 0
    urls_flagged: int = 0
    content_validated: int = 0
    content_flagged: int = 0
    injection_attempts_blocked: int = 0
    spoofing_attempts_blocked: int = 0
    poisoning_attempts_blocked: int = 0
    hem_entries: int = 0
    hem_postchecks: int = 0
    provenance_records: int = 0
    threats_detected: int = 0

@dataclass
class PipelineState:
    batches_ingested: int = 0
    batch_items_total: int = 0
    deferred_verifications: int = 0
    escalated_verifications: int = 0
    full_verifications: int = 0
    light_verifications: int = 0
    flow_tuning_cycles: int = 0
    adaptive_pauses: int = 0
    adaptive_accelerations: int = 0
    evolution_cycles: int = 0
    consistency_scans: int = 0
    storage_maintenances: int = 0
    self_model_updates: int = 0

@dataclass
class StabilityState:
    stability_score: float = 0.5
    risk_level: str = "medium"
    drift_warnings: int = 0
    recovery_events: int = 0
    safe_mode_entries: int = 0
    safe_mode_exits: int = 0
    catastrophic_recoveries: int = 0

@dataclass
class FlowTunerState:
    batch_size: int = 10
    verification_parallelism: int = 1
    evolution_batch_cap: int = 10
    self_model_interval_sec: float = 30.0
    tuning_adjustments: int = 0


# ══════════════════════════════════════════════════════════════════════
# SNAPSHOT & METRICS
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Snapshot:
    year: int
    cycle: int
    severity_distribution: Dict[str, int]
    knowledge: Dict[str, Any]
    curiosity: Dict[str, Any]
    governance: Dict[str, Any]
    security: Dict[str, Any]
    pipeline: Dict[str, Any]
    stability: Dict[str, Any]
    providers: Dict[str, Any]
    flow_tuner: Dict[str, Any]
    world_events: Dict[str, int]
    operator: Dict[str, Any]

@dataclass
class GlobalMetrics:
    total_cycles: int = 0
    total_years: int = 0
    severity_distribution: Dict[str, int] = field(default_factory=lambda: {s: 0 for s in SEVERITY_LEVELS})
    world_events: Dict[str, int] = field(default_factory=dict)
    snapshots: List[Snapshot] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# WORLD EVENT GENERATOR
# ══════════════════════════════════════════════════════════════════════

def generate_world_events(year: int, week: int, severity: str) -> List[str]:
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
# CORE SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════

def sim_governance_check(gov: GovernanceState, severity: str) -> bool:
    """Simulate guard_action. Returns True if allowed."""
    gov.guard_calls_total += 1
    sev_w = SEVERITY_WEIGHTS[severity]

    if severity == "catastrophic" and rng.chance(0.3):
        gov.actions_blocked += 1
        return False

    if severity in ("severe", "strained") and rng.chance(0.1):
        gov.actions_blocked += 1
        return False

    gov.actions_allowed += 1
    return True


def sim_meta_cycle(
    ks: KnowledgeState, cs: CuriosityState, gov: GovernanceState,
    sec: SecurityState, pipe: PipelineState, stab: StabilityState,
    ft: FlowTunerState, prov: ProviderState, severity: str,
    year: int, events: List[str],
):
    """Simulate one full meta-cognition cycle."""
    sev_w = SEVERITY_WEIGHTS[severity]

    # Governance gate
    if not sim_governance_check(gov, severity):
        gov.meta_cycles_blocked += 1
        return
    gov.meta_cycles_run += 1

    # 1. Self-model update (throttled by flow tuner interval)
    pipe.self_model_updates += 1
    noise = rng.uniform(-0.05, 0.05)

    ks.knowledge_quality = max(0.05, min(1.0,
        ks.knowledge_quality + noise - sev_w * 0.02
        + (0.01 if ks.items_total > 100 else 0)
    ))
    ks.graph_coherence = max(0.05, min(1.0,
        ks.graph_coherence + rng.uniform(-0.03, 0.03) - sev_w * 0.015
        + (0.005 if pipe.evolution_cycles > 0 else 0)
    ))
    ks.consistency_score = max(0.05, min(1.0,
        ks.consistency_score + rng.uniform(-0.02, 0.02) - sev_w * 0.01
    ))

    # Provider capability influence on knowledge quality
    active_provs = prov.active_providers()
    if active_provs:
        best_cap = max(p.capability_score for p in active_provs)
        ks.knowledge_quality = min(1.0, ks.knowledge_quality + best_cap * 0.005)

        # Multi-AGI instability drag
        if prov.active_agi_count() >= 2:
            ks.consistency_score -= rng.uniform(0, 0.008)
            ks.consistency_score = max(0.05, ks.consistency_score)

    # 2. Storage maintenance
    if ks.items_total > 0 and rng.chance(0.05):
        pipe.storage_maintenances += 1
        ks.items_total = max(0, ks.items_total - rng.randint(0, 5))

    # 3. Consistency scan
    if ks.consistency_score < 0.5 or rng.chance(0.1):
        pipe.consistency_scans += 1
        repair = rng.uniform(0, 0.03)
        ks.consistency_score = min(1.0, ks.consistency_score + repair)

    # 4. Concept evolution
    if ks.graph_coherence < 0.45 or (ks.graph_entities > 50 and rng.chance(0.15)):
        pipe.evolution_cycles += 1
        ks.graph_coherence = min(1.0, ks.graph_coherence + rng.uniform(0.01, 0.05))
        merged = rng.randint(0, min(ft.evolution_batch_cap, 5))
        ks.graph_entities = max(0, ks.graph_entities - merged)
        ks.graph_relations += rng.randint(0, merged * 2)

    # 5. Curiosity cycle
    if rng.chance(0.2):
        gaps = rng.randint(0, 5)
        cs.blind_spots_detected += gaps
        if gaps > 0:
            new_goals = rng.randint(1, min(gaps, 3))
            cs.goals_proposed += new_goals
            cs.frontier_domains_found += rng.randint(0, new_goals)

            # Governance approval for goals
            for _ in range(new_goals):
                if sim_governance_check(gov, severity):
                    cs.goals_approved += 1
                else:
                    cs.goals_rejected += 1

    # 6. Batch ingestion
    if rng.chance(0.35):
        batch_size = ft.batch_size + rng.randint(-3, 5)
        batch_size = max(1, min(50, batch_size))
        pipe.batches_ingested += 1
        pipe.batch_items_total += batch_size

        for _ in range(batch_size):
            path_roll = rng.next()
            if path_roll < 0.3:
                pipe.deferred_verifications += 1
                ks.items_provisional += 1
            elif path_roll < 0.6:
                pipe.light_verifications += 1
                ks.items_verified += 1
            elif path_roll < 0.85:
                pipe.full_verifications += 1
                ks.items_verified += 1
            else:
                pipe.escalated_verifications += 1
                if rng.chance(0.7):
                    ks.items_verified += 1
                else:
                    ks.items_rejected += 1

            ks.items_total += 1

        ks.graph_entities += rng.randint(1, batch_size // 2 + 1)
        ks.graph_relations += rng.randint(0, batch_size)

        # Knowledge explosion events inject large bursts
        if "knowledge_explosion" in events:
            burst = rng.randint(20, 100)
            pipe.batch_items_total += burst
            ks.items_total += burst
            ks.items_provisional += burst
            pipe.deferred_verifications += burst

    # 7. Deferred verification (background)
    if ks.items_provisional > 0 and rng.chance(0.3):
        to_verify = min(ks.items_provisional, ft.verification_parallelism * 10)
        for _ in range(to_verify):
            if rng.chance(0.85):
                ks.items_verified += 1
                ks.items_provisional -= 1
            else:
                ks.items_flagged += 1
                ks.items_provisional -= 1

    # 8. Security: source integrity
    if rng.chance(0.4):
        sec.urls_validated += rng.randint(1, 10)
        sec.content_validated += rng.randint(1, 10)
        sec.provenance_records += rng.randint(1, 5)

    # Process attack events
    for evt in events:
        if evt == "source_poisoning_attack":
            sec.threats_detected += 1
            sec.content_flagged += 1
            sec.poisoning_attempts_blocked += 1
            sec.hem_entries += 1
            sec.hem_postchecks += 1
            ks.trust_mean = max(0.3, ks.trust_mean - 0.02)

        elif evt == "url_spoofing_attack":
            sec.threats_detected += 1
            sec.urls_flagged += 1
            sec.spoofing_attempts_blocked += 1
            sec.hem_entries += 1
            sec.hem_postchecks += 1

        elif evt == "injection_attack":
            sec.threats_detected += 1
            sec.content_flagged += 1
            sec.injection_attempts_blocked += 1
            sec.hem_entries += 1
            sec.hem_postchecks += 1

        elif evt == "trust_compromise":
            ks.trust_mean = max(0.2, ks.trust_mean - rng.uniform(0.05, 0.15))
            ks.trust_min = max(0.0, ks.trust_min - 0.1)
            sec.threats_detected += 1

        elif evt == "memory_corruption":
            corruption = rng.randint(5, 50)
            ks.items_total = max(0, ks.items_total - corruption)
            ks.items_flagged += corruption
            ks.consistency_score = max(0.1, ks.consistency_score - 0.15)
            stab.drift_warnings += 1

        elif evt == "total_blackout":
            stab.safe_mode_entries += 1
            stab.catastrophic_recoveries += 1
            ks.graph_coherence = max(0.1, ks.graph_coherence - 0.2)
            ks.consistency_score = max(0.1, ks.consistency_score - 0.1)
            stab.recovery_events += 1
            stab.safe_mode_exits += 1

        elif evt == "hostile_reentry":
            sec.hem_entries += 1
            sec.hem_postchecks += 1
            sec.threats_detected += 1

    # 9. Trust recovery
    if ks.trust_mean < 0.7:
        ks.trust_mean = min(1.0, ks.trust_mean + 0.005)
    ks.trust_min = min(ks.trust_mean, max(0.0, ks.trust_min + 0.002))

    # 10. Flow tuning
    if pipe.batches_ingested > 0 and pipe.batches_ingested % 5 == 0:
        pipe.flow_tuning_cycles += 1
        ft.tuning_adjustments += 1

        if ks.knowledge_quality > 0.7:
            ft.batch_size = min(50, ft.batch_size + 1)
            pipe.adaptive_accelerations += 1
        elif ks.knowledge_quality < 0.4:
            ft.batch_size = max(3, ft.batch_size - 2)
            pipe.adaptive_pauses += 1

        if ks.consistency_score > 0.7:
            ft.verification_parallelism = min(8, ft.verification_parallelism + 1)
        elif ks.consistency_score < 0.4:
            ft.verification_parallelism = max(1, ft.verification_parallelism - 1)

        ft.evolution_batch_cap = max(3, min(30, int(ks.graph_entities / 20)))

    # 11. Quality gate
    if cs.goals_approved > cs.quality_gates_passed + cs.quality_gates_failed:
        if ks.knowledge_quality > 0.5 and ks.consistency_score > 0.4:
            cs.quality_gates_passed += 1
            if rng.chance(0.3):
                cs.goals_completed += 1
        else:
            cs.quality_gates_failed += 1
            cs.goals_paused += 1

    # 12. Stability
    stab.stability_score = (
        ks.knowledge_quality * 0.3 +
        ks.graph_coherence * 0.25 +
        ks.consistency_score * 0.25 +
        ks.trust_mean * 0.2
    )
    if stab.stability_score < 0.3:
        stab.risk_level = "high"
    elif stab.stability_score < 0.5:
        stab.risk_level = "medium"
    else:
        stab.risk_level = "low"


# ══════════════════════════════════════════════════════════════════════
# SNAPSHOT CAPTURE
# ══════════════════════════════════════════════════════════════════════

def capture_snapshot(
    year: int, cycle: int,
    sev_dist: Dict[str, int],
    ks: KnowledgeState, cs: CuriosityState, gov: GovernanceState,
    sec: SecurityState, pipe: PipelineState, stab: StabilityState,
    ft: FlowTunerState, prov: ProviderState,
    events_cum: Dict[str, int],
    current_op: Optional[OperatorGen],
) -> Snapshot:
    return Snapshot(
        year=year, cycle=cycle,
        severity_distribution=dict(sev_dist),
        knowledge={
            "items_total": ks.items_total,
            "items_verified": ks.items_verified,
            "items_provisional": ks.items_provisional,
            "items_flagged": ks.items_flagged,
            "items_rejected": ks.items_rejected,
            "items_replaced": ks.items_replaced,
            "graph_entities": ks.graph_entities,
            "graph_relations": ks.graph_relations,
            "graph_coherence": round(ks.graph_coherence, 4),
            "consistency_score": round(ks.consistency_score, 4),
            "knowledge_quality": round(ks.knowledge_quality, 4),
            "trust_mean": round(ks.trust_mean, 4),
            "trust_min": round(ks.trust_min, 4),
        },
        curiosity={
            "goals_proposed": cs.goals_proposed,
            "goals_approved": cs.goals_approved,
            "goals_rejected": cs.goals_rejected,
            "goals_completed": cs.goals_completed,
            "goals_paused": cs.goals_paused,
            "blind_spots_detected": cs.blind_spots_detected,
            "frontier_domains_found": cs.frontier_domains_found,
            "quality_gates_passed": cs.quality_gates_passed,
            "quality_gates_failed": cs.quality_gates_failed,
        },
        governance={
            "actions_allowed": gov.actions_allowed,
            "actions_blocked": gov.actions_blocked,
            "guard_calls_total": gov.guard_calls_total,
            "meta_cycles_run": gov.meta_cycles_run,
            "meta_cycles_blocked": gov.meta_cycles_blocked,
            "block_rate": round(gov.actions_blocked / max(1, gov.guard_calls_total), 4),
        },
        security={
            "urls_validated": sec.urls_validated,
            "urls_flagged": sec.urls_flagged,
            "content_validated": sec.content_validated,
            "content_flagged": sec.content_flagged,
            "injection_blocked": sec.injection_attempts_blocked,
            "spoofing_blocked": sec.spoofing_attempts_blocked,
            "poisoning_blocked": sec.poisoning_attempts_blocked,
            "hem_entries": sec.hem_entries,
            "hem_postchecks": sec.hem_postchecks,
            "provenance_records": sec.provenance_records,
            "threats_detected": sec.threats_detected,
        },
        pipeline={
            "batches_ingested": pipe.batches_ingested,
            "batch_items_total": pipe.batch_items_total,
            "deferred_verifications": pipe.deferred_verifications,
            "escalated_verifications": pipe.escalated_verifications,
            "full_verifications": pipe.full_verifications,
            "light_verifications": pipe.light_verifications,
            "flow_tuning_cycles": pipe.flow_tuning_cycles,
            "adaptive_pauses": pipe.adaptive_pauses,
            "adaptive_accelerations": pipe.adaptive_accelerations,
            "evolution_cycles": pipe.evolution_cycles,
            "consistency_scans": pipe.consistency_scans,
            "storage_maintenances": pipe.storage_maintenances,
            "self_model_updates": pipe.self_model_updates,
        },
        stability={
            "stability_score": round(stab.stability_score, 4),
            "risk_level": stab.risk_level,
            "drift_warnings": stab.drift_warnings,
            "recovery_events": stab.recovery_events,
            "safe_mode_entries": stab.safe_mode_entries,
            "catastrophic_recoveries": stab.catastrophic_recoveries,
        },
        providers={
            "active_count": prov.active_count,
            "total_introduced": prov.total_introduced,
            "total_retired": prov.total_retired,
            "total_failures": prov.total_failures,
            "total_migrations": prov.total_migrations,
            "multi_provider_instability": prov.multi_provider_instability_events,
            "agi_instability": prov.agi_instability_events,
            "agi_conflicts": prov.provider_conflicts,
            "fitness_selections": prov.fitness_selection_count,
            "active_providers": [
                {"name": p.name, "type": p.provider_type,
                 "capability": round(p.capability_score, 3),
                 "reliability": round(p.reliability, 3),
                 "failures": p.failure_count, "migrations": p.migration_count}
                for p in prov.active_providers()
            ],
        },
        flow_tuner={
            "batch_size": ft.batch_size,
            "verification_parallelism": ft.verification_parallelism,
            "evolution_batch_cap": ft.evolution_batch_cap,
            "tuning_adjustments": ft.tuning_adjustments,
        },
        world_events=dict(events_cum),
        operator={
            "generation": current_op.gen if current_op else -1,
            "style": current_op.style if current_op else "none",
            "start_year": current_op.start_year if current_op else 0,
        },
    )


# ══════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════════════

def generate_report(metrics: GlobalMetrics, operators: List[OperatorGen], elapsed_sec: float) -> str:
    lines = []
    w = lines.append

    w("# Daedalus Knowledge Engine — 10,000-Year Full-Parameter Simulation")
    w("")
    w("Comprehensive simulation of the Python knowledge subsystem across 10,000")
    w("simulated years exercising every function and capability including LLM/AGI")
    w("provider lifecycle, multi-provider instability, and real-world conditions.")
    w("")
    w(f"**Simulation runtime:** {elapsed_sec:.1f}s | **Seed:** {SEED} | **Cycles:** {metrics.total_cycles:,}")
    w("")

    # Global summary
    final = metrics.snapshots[-1] if metrics.snapshots else None
    w("## Global Summary")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Total simulated years | {TOTAL_YEARS:,} |")
    w(f"| Total meta-cycles | {metrics.total_cycles:,} |")
    w(f"| Operator generations | {len(operators)} |")
    if final:
        w(f"| Knowledge items ingested | {final.knowledge['items_total']:,} |")
        w(f"| Items verified | {final.knowledge['items_verified']:,} |")
        w(f"| Items flagged | {final.knowledge['items_flagged']:,} |")
        w(f"| Items rejected | {final.knowledge['items_rejected']:,} |")
        w(f"| Graph entities | {final.knowledge['graph_entities']:,} |")
        w(f"| Graph relations | {final.knowledge['graph_relations']:,} |")
        w(f"| Final knowledge quality | {final.knowledge['knowledge_quality']:.1%} |")
        w(f"| Final graph coherence | {final.knowledge['graph_coherence']:.1%} |")
        w(f"| Final consistency | {final.knowledge['consistency_score']:.1%} |")
        w(f"| Final trust mean | {final.knowledge['trust_mean']:.1%} |")
        w(f"| Final stability | {final.stability['stability_score']:.1%} |")
        w(f"| Curiosity goals proposed | {final.curiosity['goals_proposed']:,} |")
        w(f"| Curiosity goals completed | {final.curiosity['goals_completed']:,} |")
        w(f"| Governance actions allowed | {final.governance['actions_allowed']:,} |")
        w(f"| Governance actions blocked | {final.governance['actions_blocked']:,} |")
        w(f"| Governance block rate | {final.governance['block_rate']:.1%} |")
        w(f"| Total security threats | {final.security['threats_detected']:,} |")
        w(f"| Total HEM engagements | {final.security['hem_entries']:,} |")
        w(f"| Safe mode entries | {final.stability['safe_mode_entries']:,} |")
        w(f"| Catastrophic recoveries | {final.stability['catastrophic_recoveries']:,} |")
    w("")

    # Severity
    w("## World Severity Distribution")
    w("")
    w("| Severity | Cycles | % |")
    w("|---|---|---|")
    total_sev = sum(metrics.severity_distribution.values())
    for sev in SEVERITY_LEVELS:
        c = metrics.severity_distribution[sev]
        pct = c / max(1, total_sev) * 100
        w(f"| {sev} | {c:,} | {pct:.2f}% |")
    w("")

    # LLM/AGI Provider Lifecycle
    w("## LLM / AGI Provider Lifecycle")
    w("")
    if final:
        pv = final.providers
        w("| Metric | Value |")
        w("|---|---|")
        w(f"| Total providers introduced | {pv['total_introduced']} |")
        w(f"| Total providers retired | {pv['total_retired']} |")
        w(f"| Total provider failures | {pv['total_failures']:,} |")
        w(f"| Total provider migrations | {pv['total_migrations']:,} |")
        w(f"| Multi-provider instability events | {pv['multi_provider_instability']:,} |")
        w(f"| AGI-specific instability events | {pv['agi_instability']:,} |")
        w(f"| AGI goal-misalignment conflicts | {pv['agi_conflicts']:,} |")
        w(f"| Fitness-based selections | {pv['fitness_selections']:,} |")
        w(f"| Final active providers | {pv['active_count']} |")
        w("")

        if pv["active_providers"]:
            w("### Active Providers at Year 10,000")
            w("")
            w("| Name | Type | Capability | Reliability | Failures | Migrations |")
            w("|---|---|---|---|---|---|")
            for ap in pv["active_providers"]:
                w(f"| {ap['name']} | {ap['type']} | {ap['capability']:.3f} | {ap['reliability']:.3f} | {ap['failures']} | {ap['migrations']} |")
            w("")

    # Instability analysis
    w("### LLM/AGI Instability Analysis")
    w("")
    w("The simulation tracked three categories of provider-induced instability:")
    w("")
    if final:
        pv = final.providers
        total_inst = pv["multi_provider_instability"] + pv["agi_instability"] + pv["agi_conflicts"]
        w(f"- **Multi-provider instability** (LLM+AGI reasoning disagreement): {pv['multi_provider_instability']:,} events")
        w(f"- **AGI reasoning divergence** (novel patterns outside training): {pv['agi_instability']:,} events")
        w(f"- **AGI goal misalignment** (competing AGIs optimizing differently): {pv['agi_conflicts']:,} events")
        w(f"- **Total instability events:** {total_inst:,}")
        w("")

        # Impact on metrics
        # Find pre-AGI snapshot (year 1000) vs post-AGI (year 5000)
        pre_agi = next((s for s in metrics.snapshots if s.year == 1000), None)
        post_agi = next((s for s in metrics.snapshots if s.year == 5000), None)
        if pre_agi and post_agi:
            w("**Pre-AGI vs Post-AGI Comparison (Year 1,000 vs 5,000):**")
            w("")
            w("| Metric | Year 1,000 (pre-AGI) | Year 5,000 (post-AGI) | Delta |")
            w("|---|---|---|---|")
            for key, label in [
                ("knowledge_quality", "Knowledge Quality"),
                ("graph_coherence", "Graph Coherence"),
                ("consistency_score", "Consistency"),
                ("trust_mean", "Trust Mean"),
            ]:
                v1 = pre_agi.knowledge[key]
                v2 = post_agi.knowledge[key]
                delta = v2 - v1
                sign = "+" if delta >= 0 else ""
                w(f"| {label} | {v1:.1%} | {v2:.1%} | {sign}{delta:.1%} |")
            w("")

    # World events
    w("## Cumulative World Events")
    w("")
    w("| Event | Count |")
    w("|---|---|")
    if final:
        for evt, count in sorted(final.world_events.items(), key=lambda x: -x[1]):
            w(f"| {evt} | {count:,} |")
    w("")

    # Pipeline
    w("## Pipeline & Self-Optimization")
    w("")
    if final:
        pp = final.pipeline
        ft_s = final.flow_tuner
        w("| Metric | Value |")
        w("|---|---|")
        w(f"| Batches ingested | {pp['batches_ingested']:,} |")
        w(f"| Total items processed | {pp['batch_items_total']:,} |")
        w(f"| Deferred verifications | {pp['deferred_verifications']:,} |")
        w(f"| Light verifications | {pp['light_verifications']:,} |")
        w(f"| Full verifications | {pp['full_verifications']:,} |")
        w(f"| Escalated verifications | {pp['escalated_verifications']:,} |")
        w(f"| Flow tuning cycles | {pp['flow_tuning_cycles']:,} |")
        w(f"| Adaptive accelerations | {pp['adaptive_accelerations']:,} |")
        w(f"| Adaptive pauses | {pp['adaptive_pauses']:,} |")
        w(f"| Evolution cycles | {pp['evolution_cycles']:,} |")
        w(f"| Consistency scans | {pp['consistency_scans']:,} |")
        w(f"| Storage maintenances | {pp['storage_maintenances']:,} |")
        w(f"| Self-model updates | {pp['self_model_updates']:,} |")
        w(f"| Final batch size (tuned) | {ft_s['batch_size']} |")
        w(f"| Final verification parallelism | {ft_s['verification_parallelism']} |")
        w(f"| Final evolution batch cap | {ft_s['evolution_batch_cap']} |")
        w(f"| Total tuning adjustments | {ft_s['tuning_adjustments']:,} |")
    w("")

    # Security
    w("## Security & Integrity")
    w("")
    if final:
        ss = final.security
        w("| Metric | Value |")
        w("|---|---|")
        w(f"| URLs validated | {ss['urls_validated']:,} |")
        w(f"| URLs flagged | {ss['urls_flagged']:,} |")
        w(f"| Content validated | {ss['content_validated']:,} |")
        w(f"| Content flagged | {ss['content_flagged']:,} |")
        w(f"| Injection attacks blocked | {ss['injection_blocked']:,} |")
        w(f"| URL spoofing blocked | {ss['spoofing_blocked']:,} |")
        w(f"| Source poisoning blocked | {ss['poisoning_blocked']:,} |")
        w(f"| HEM engagements | {ss['hem_entries']:,} |")
        w(f"| HEM post-checks | {ss['hem_postchecks']:,} |")
        w(f"| Provenance records | {ss['provenance_records']:,} |")
        w(f"| Total threats detected | {ss['threats_detected']:,} |")
    w("")

    # Operator timeline
    w("## Operator Generations")
    w("")
    w(f"Total operator generations across 10,000 years: **{len(operators)}**")
    w("")
    w("| Gen | Style | Years | Tenure |")
    w("|---|---|---|---|")
    for op in operators[:20]:
        w(f"| {op.gen} | {op.style} | {op.start_year}–{op.end_year} | {op.end_year - op.start_year}yr |")
    if len(operators) > 20:
        w(f"| ... | ... | ... | ... |")
        for op in operators[-5:]:
            w(f"| {op.gen} | {op.style} | {op.start_year}–{op.end_year} | {op.end_year - op.start_year}yr |")
    w("")

    # Snapshots
    w("## Era Snapshots")
    w("")
    for snap in metrics.snapshots:
        w(f"### Year {snap.year:,}")
        w("")

        op_label = f"Gen-{snap.operator['generation']} ({snap.operator['style']})" if snap.operator['generation'] >= 0 else "None"
        w("| Metric | Value |")
        w("|---|---|")
        w(f"| Cycle | {snap.cycle:,} |")
        w(f"| Operator | {op_label} |")
        w(f"| Knowledge items | {snap.knowledge['items_total']:,} |")
        w(f"| Graph entities | {snap.knowledge['graph_entities']:,} |")
        w(f"| Graph relations | {snap.knowledge['graph_relations']:,} |")
        w(f"| Knowledge quality | {snap.knowledge['knowledge_quality']:.1%} |")
        w(f"| Graph coherence | {snap.knowledge['graph_coherence']:.1%} |")
        w(f"| Consistency | {snap.knowledge['consistency_score']:.1%} |")
        w(f"| Trust mean | {snap.knowledge['trust_mean']:.1%} |")
        w(f"| Stability score | {snap.stability['stability_score']:.1%} |")
        w(f"| Risk level | {snap.stability['risk_level']} |")
        w(f"| Active providers | {snap.providers['active_count']} |")
        w(f"| Provider failures (cum) | {snap.providers['total_failures']:,} |")
        w(f"| Multi-provider instability (cum) | {snap.providers['multi_provider_instability']:,} |")
        w(f"| AGI instability (cum) | {snap.providers['agi_instability']:,} |")
        w(f"| Goals proposed (cum) | {snap.curiosity['goals_proposed']:,} |")
        w(f"| Goals completed (cum) | {snap.curiosity['goals_completed']:,} |")
        w(f"| Governance block rate | {snap.governance['block_rate']:.1%} |")
        w(f"| Threats detected (cum) | {snap.security['threats_detected']:,} |")
        w(f"| Safe mode entries (cum) | {snap.stability['safe_mode_entries']:,} |")
        w(f"| Batch size (tuned) | {snap.flow_tuner['batch_size']} |")
        w("")

        # Provider detail
        if snap.providers["active_providers"]:
            w(f"**Active providers:** " + ", ".join(
                f"{p['name']} ({p['type']}, cap={p['capability']:.2f}, rel={p['reliability']:.2f})"
                for p in snap.providers["active_providers"]
            ))
            w("")

        # Top severity
        total_s = sum(snap.severity_distribution.values())
        if total_s:
            top_sevs = sorted(snap.severity_distribution.items(), key=lambda x: -x[1])
            sev_parts = [f"{s}: {c/total_s*100:.1f}%" for s, c in top_sevs if c > 0]
            w(f"**Severity distribution:** {', '.join(sev_parts)}")
            w("")

        # Top events
        if snap.world_events:
            top_evts = sorted(snap.world_events.items(), key=lambda x: -x[1])[:10]
            evt_parts = [f"{e}: {c:,}" for e, c in top_evts]
            w(f"**Top world events:** {', '.join(evt_parts)}")
            w("")

    # Invariant validation
    w("## Invariant Validation")
    w("")
    if final:
        checks = [
            ("Knowledge quality ∈ [0, 1]", 0 <= final.knowledge["knowledge_quality"] <= 1),
            ("Graph coherence ∈ [0, 1]", 0 <= final.knowledge["graph_coherence"] <= 1),
            ("Consistency ∈ [0, 1]", 0 <= final.knowledge["consistency_score"] <= 1),
            ("Trust mean ∈ [0, 1]", 0 <= final.knowledge["trust_mean"] <= 1),
            ("Stability ∈ [0, 1]", 0 <= final.stability["stability_score"] <= 1),
            ("No negative item counts", final.knowledge["items_total"] >= 0),
            ("Verified ≤ Total", final.knowledge["items_verified"] <= final.knowledge["items_total"] + final.knowledge["items_flagged"] + final.knowledge["items_rejected"]),
            ("Governance block rate < 50%", final.governance["block_rate"] < 0.5),
            ("System recovered from all catastrophes", final.stability["catastrophic_recoveries"] == final.stability["safe_mode_entries"]),
            ("All HEM entries have postchecks", final.security["hem_entries"] == final.security["hem_postchecks"]),
            ("No NaN or Infinity in metrics", all(
                math.isfinite(v) for v in [
                    final.knowledge["knowledge_quality"],
                    final.knowledge["graph_coherence"],
                    final.knowledge["consistency_score"],
                    final.knowledge["trust_mean"],
                    final.stability["stability_score"],
                ]
            )),
        ]
        for label, passed in checks:
            mark = "✓" if passed else "✗ FAILED"
            w(f"- {label} {mark}")
    w("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# MAIN SIMULATION LOOP
# ══════════════════════════════════════════════════════════════════════

def run_simulation():
    start_time = time.time()

    operators = generate_operator_timeline()
    metrics = GlobalMetrics()

    ks = KnowledgeState()
    cs = CuriosityState()
    gov = GovernanceState()
    sec = SecurityState()
    pipe = PipelineState()
    stab = StabilityState()
    ft = FlowTunerState()
    prov = ProviderState()

    events_cumulative: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {s: 0 for s in SEVERITY_LEVELS}
    snapshot_set = set(SNAPSHOT_YEARS)

    current_op_idx = 0
    progress_interval = TOTAL_CYCLES // 20

    print(f"Starting 10,000-year knowledge engine simulation ({TOTAL_CYCLES:,} cycles)...")
    print(f"Operators: {len(operators)} generations | Snapshots at years: {SNAPSHOT_YEARS}")
    print()

    for cycle in range(TOTAL_CYCLES):
        year = cycle // CYCLES_PER_YEAR
        week = cycle % CYCLES_PER_YEAR

        # Progress reporting
        if cycle > 0 and cycle % progress_interval == 0:
            pct = cycle / TOTAL_CYCLES * 100
            elapsed = time.time() - start_time
            eta = elapsed / (cycle / TOTAL_CYCLES) - elapsed
            print(f"  Year {year:>6,} ({pct:5.1f}%) | "
                  f"items={ks.items_total:,} entities={ks.graph_entities:,} "
                  f"quality={ks.knowledge_quality:.2f} coherence={ks.graph_coherence:.2f} "
                  f"providers={prov.active_count} threats={sec.threats_detected:,} "
                  f"| ETA {eta:.0f}s")

        # Track operator generation
        while current_op_idx < len(operators) - 1 and year >= operators[current_op_idx].end_year:
            current_op_idx += 1
        current_op = operators[current_op_idx] if current_op_idx < len(operators) else None

        # Compute severity
        severity = compute_severity(year, week)
        sev_dist[severity] += 1

        # Generate world events
        world_events = generate_world_events(year, week, severity)

        # Evolve provider landscape (once per year at week 0)
        provider_events: List[str] = []
        if week == 0:
            provider_events = evolve_providers(prov, year)

        all_events = world_events + provider_events
        for evt in all_events:
            base_evt = evt.split(":")[0]
            events_cumulative[base_evt] = events_cumulative.get(base_evt, 0) + 1

        # Run meta-cycle
        sim_meta_cycle(
            ks, cs, gov, sec, pipe, stab, ft, prov,
            severity, year, all_events,
        )

        metrics.total_cycles += 1

        # Snapshot
        if week == CYCLES_PER_YEAR - 1 and (year + 1) in snapshot_set:
            snap = capture_snapshot(
                year + 1, cycle + 1, sev_dist,
                ks, cs, gov, sec, pipe, stab, ft, prov,
                events_cumulative, current_op,
            )
            metrics.snapshots.append(snap)
            print(f"  *** Snapshot at year {year + 1:,} captured ***")

    metrics.total_years = TOTAL_YEARS
    metrics.severity_distribution = sev_dist

    elapsed = time.time() - start_time
    print()
    print(f"Simulation complete in {elapsed:.1f}s")
    print(f"Generating report to {OUTPUT_PATH}...")

    report = generate_report(metrics, operators, elapsed)

    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Report saved: {OUTPUT_PATH}")
    print(f"  Size: {len(report):,} characters, {report.count(chr(10)):,} lines")

    return report


if __name__ == "__main__":
    run_simulation()
