#!/usr/bin/env python3
"""
DAEDALUS — 10,000-YEAR UNIFIED BEING SIMULATION (Realistic Model)
===================================================================

Scientific simulation of the Daedalus cognitive entity. All metrics are
DERIVED from concrete state — never evolved independently. The sim models
actual operations (ingestion, verification, consolidation, compaction)
and computes metrics as observable functions of the resulting state.

Design principles:
  1. Metrics = lenses on state, not independent variables
  2. No random walks on metrics, no artificial uplifts or floors
  3. Operations have real costs and realistic success rates
  4. Severity affects INPUT quality, not metrics directly
  5. Both "measured" (what Daedalus sees) and "actual" (ground truth) shown
  6. Natural tradeoffs emerge: speed vs quality, growth vs maintenance

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
TOTAL_REAL_YEARS = 1_000
CYCLE_CADENCE_MINUTES = 15
CYCLES_PER_REAL_YEAR = int(365.25 * 24 * 60 / CYCLE_CADENCE_MINUTES)  # 35,064
TOTAL_CYCLES = TOTAL_REAL_YEARS * CYCLES_PER_REAL_YEAR  # 35,064,000

# Back-compat aliases used by existing code
TOTAL_YEARS = TOTAL_REAL_YEARS
CYCLES_PER_YEAR = CYCLES_PER_REAL_YEAR

SNAPSHOT_YEARS = [1, 5, 10, 25, 50, 100, 250, 500, 1_000]

# Scale factor: all probabilities designed for weekly cadence (52/yr)
# must be multiplied by this to match the 15-minute cadence (35064/yr)
CYCLE_SCALE = 52.0 / CYCLES_PER_REAL_YEAR  # ~0.00148

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "SIMULATION_UNIFIED_BEING_10KYR.md"


# =====================================================================
# DETERMINISTIC RNG (Mulberry32)
# =====================================================================

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


# =====================================================================
# SEVERITY MODEL (stochastic with era baseline)
# =====================================================================

SEVERITY_LEVELS = [
    "healthy", "mild", "moderate", "stressed",
    "strained", "severe", "catastrophic",
]

SEVERITY_WEIGHTS = {
    "healthy": 0.0, "mild": 0.1, "moderate": 0.25,
    "stressed": 0.4, "strained": 0.55, "severe": 0.75, "catastrophic": 0.95,
}


def compute_severity(year: int, week: int) -> str:
    """
    Two-layer severity model for real calendar time:
      1. Era baseline: 50-year cycle (societal/technological shifts)
      2. Stochastic variation: random events within each era

    Each era is distinct. The deterministic pattern provides structure;
    the stochastic layer makes each era play out differently.
    """
    era_year = year % 50

    if era_year < 2:
        baseline = 0.65
    elif era_year < 5:
        baseline = 0.40
    elif era_year < 10:
        baseline = 0.25
    elif era_year < 35:
        baseline = 0.08
    elif era_year < 45:
        baseline = 0.20
    else:
        baseline = 0.45

    variation = rng.uniform(-0.15, 0.15)
    score = max(0.0, min(1.0, baseline + variation))

    if score < 0.05:
        return "healthy"
    if score < 0.15:
        return "mild"
    if score < 0.30:
        return "moderate"
    if score < 0.45:
        return "stressed"
    if score < 0.60:
        return "strained"
    if score < 0.80:
        return "severe"
    return "catastrophic"


# =====================================================================
# PROVIDER LIFECYCLE
# =====================================================================

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
    transition_events: int = 0
    llm_hallucination_items: int = 0

    # Cached per-year values (refreshed in evolve_providers)
    _best_cap: float = 0.0
    _avg_rel: float = 0.5
    _agi_count: int = 0
    _active_list: List[Any] = field(default_factory=list)

    def _refresh_cache(self):
        a = [p for p in self.providers if p.is_active]
        self._active_list = a
        self.active_count = len(a)
        self._best_cap = max((p.capability for p in a), default=0.0)
        self._avg_rel = sum(p.reliability for p in a) / len(a) if a else 0.5
        self._agi_count = sum(1 for p in a if p.provider_type == "agi")

    def active(self) -> List[SimProvider]:
        return self._active_list

    def active_agi_count(self) -> int:
        return self._agi_count

    def best_capability(self) -> float:
        return self._best_cap

    def avg_reliability(self) -> float:
        return self._avg_rel


def _tech_level(year: int) -> float:
    """Technology capability baseline — logarithmic growth with ceiling."""
    return min(0.96, 0.45 + 0.12 * math.log1p(year / 5.0))


def evolve_providers(state: ProviderState, year: int) -> List[str]:
    events = []

    # --- Year 0: LLM available from day 1 (operator need) ---
    if year == 0 and not state.providers:
        state.providers.append(
            SimProvider("llm-gen0", "LLM-Gen0", "llm", 0.45, 0.85, 0))
        state.total_introduced += 1
        events.append("provider_introduced:LLM-Gen0(early)")

    # --- Procedural LLM introduction every 2-4 years ---
    tech = _tech_level(year)
    if year >= 2:
        llm_interval = 3
        if year % llm_interval == 0 and rng.chance(0.75):
            gen = state.total_introduced
            cap = min(0.98, tech + rng.uniform(-0.03, 0.08))
            rel = rng.uniform(0.82, 0.96)
            p = SimProvider(f"llm-gen{gen}", f"LLM-Gen{gen}", "llm", cap, rel, year)
            state.providers.append(p)
            state.total_introduced += 1
            events.append(f"provider_introduced:{p.name}")

    # --- Procedural AGI introduction starting ~year 15, every 6-8 years ---
    if year >= 15:
        agi_interval = 7
        if (year - 15) % agi_interval == 0 and rng.chance(0.55):
            gen = state.total_introduced
            cap = min(0.99, tech + rng.uniform(0.03, 0.12))
            rel = rng.uniform(0.76, 0.92)
            p = SimProvider(f"agi-gen{gen}", f"AGI-Gen{gen}", "agi", cap, rel, year)
            state.providers.append(p)
            state.total_introduced += 1
            events.append(f"provider_introduced:{p.name}(AGI)")

    # --- Retirement: LLMs after 3-8yr, AGIs after 8-15yr ---
    for p in list(state.active()):
        age = year - p.year_introduced
        if p.provider_type == "llm" and age >= 4:
            retire_chance = 0.25 + (age - 4) * 0.10
            if rng.chance(min(0.80, retire_chance)):
                p.is_active = False
                p.year_retired = year
                state.total_retired += 1
                state.transition_events += 1
                events.append(f"provider_retired:{p.name}")
        elif p.provider_type == "agi" and age >= 9:
            retire_chance = 0.15 + (age - 9) * 0.06
            if rng.chance(min(0.70, retire_chance)):
                p.is_active = False
                p.year_retired = year
                state.total_retired += 1
                state.transition_events += 1
                events.append(f"provider_retired:{p.name}")

    # --- Capability drift: active providers slowly improve ---
    for p in state.active():
        if rng.chance(0.15):
            p.capability = min(0.99, p.capability + rng.uniform(0.001, 0.01))

    # --- Failures and reliability degradation ---
    for p in state.active():
        fail_chance = (1.0 - p.reliability) * 0.02
        if rng.chance(fail_chance):
            p.failures += 1
            state.total_failures += 1
            events.append(f"provider_failure:{p.name}")
            if p.failures > 5 and rng.chance(0.25):
                p.reliability = max(0.5, p.reliability - 0.03)
        else:
            p.successes += 1

    # --- Multi-provider instability ---
    active = state.active()
    if len(active) >= 3:
        if rng.chance(0.04):
            state.multi_instability += 1
            events.append("multi_provider_instability")

    agi_count = sum(1 for p in active if p.provider_type == "agi")
    if agi_count >= 2:
        if rng.chance(0.06):
            state.agi_instability += 1
            events.append("agi_instability")
        if rng.chance(0.02):
            state.agi_conflicts += 1
            events.append("agi_conflict")

    # --- Migrations (provider moves to different hardware) ---
    if len(active) >= 2 and rng.chance(0.08):
        p = rng.choice(active)
        p.migrations += 1
        state.total_migrations += 1
        events.append(f"provider_migration:{p.name}")

    # --- Prune retired providers older than 30 years (memory optimization) ---
    state.providers = [
        p for p in state.providers
        if p.is_active or (p.year_retired is not None and year - p.year_retired < 30)
    ]

    # --- Refresh cache ---
    state._refresh_cache()
    return events


# =====================================================================
# OPERATOR LIFECYCLE
# =====================================================================

OPERATOR_STYLES = ["pioneer", "steward", "guardian", "delegator", "architect"]


@dataclass
class OperatorGen:
    gen: int
    style: str
    start_year: int
    end_year: int


def generate_operator_timeline() -> List[OperatorGen]:
    """Operators serve 5-30 real year tenures (career spans)."""
    ops, year, gen = [], 0, 0
    while year < TOTAL_YEARS:
        tenure = rng.randint(5, 30)
        end = min(year + tenure, TOTAL_YEARS)
        ops.append(OperatorGen(gen, OPERATOR_STYLES[gen % len(OPERATOR_STYLES)], year, end))
        year = end
        gen += 1
    return ops


# =====================================================================
# UNIFIED BEING STATE — concrete items, derived metrics
# =====================================================================

@dataclass
class BeingState:
    """
    Complete state of the Daedalus being. All metrics are computed from
    concrete item/graph counts — never set directly.

    Item lifecycle:
      ingested -> provisional -> (verified -> clean) OR (rejected -> removed)
      clean -> stale (time decay)
      stale -> clean (refreshed by maintenance)
      contaminated items look clean but are bad (ground truth only)
    """

    # === Active KB (partition of all items) ===
    items_clean: int = 0           # Verified, fresh, no known issues
    items_provisional: int = 0     # Ingested, awaiting verification
    items_stale: int = 0           # Were clean, now outdated
    items_flagged: int = 0         # Found to have issues, quarantined
    items_contaminated: int = 0    # Bad items that look clean (HIDDEN)

    # === Issue tracking ===
    contradictions_active: int = 0  # Discovered but unresolved
    contradictions_latent: int = 0  # Exist but not yet discovered (HIDDEN)

    # === Knowledge graph ===
    graph_entities: int = 0
    graph_orphans: int = 0         # Entities with zero relations
    graph_relations: int = 0
    graph_components: int = 1

    # === Source tracking ===
    source_verifications: int = 0  # Successful source verifications
    source_failures: int = 0       # Source verification failures

    # === Cumulative counters ===
    total_ingested: int = 0
    total_verified: int = 0
    total_rejected: int = 0
    total_removed: int = 0
    total_refreshed: int = 0
    total_contradictions_found: int = 0
    total_contradictions_resolved: int = 0
    contradictions_removed_by_cleanup: int = 0  # removed via sweep, not formal resolution
    total_contamination_discovered: int = 0

    # === Attack history ===
    attacks_total: int = 0
    attacks_blocked: int = 0
    attacks_leaked: int = 0

    # === Governance ===
    guard_calls: int = 0
    actions_allowed: int = 0
    actions_blocked: int = 0
    meta_cycles_run: int = 0
    meta_cycles_blocked: int = 0
    severity_blocks: int = 0

    # === Security ===
    hem_entries: int = 0
    hem_postchecks: int = 0
    threats_detected: int = 0
    attack_sweeps: int = 0
    attack_sweep_flagged: int = 0

    # === Goals ===
    goals_proposed: int = 0
    goals_approved: int = 0
    goals_rejected: int = 0
    goals_completed: int = 0
    goals_paused: int = 0
    goals_expired: int = 0
    goals_backpressure_skips: int = 0

    # === Pipeline ===
    batches: int = 0
    verification_cycles: int = 0
    consolidation_cycles: int = 0
    compaction_cycles: int = 0
    refresh_cycles: int = 0
    maintenance_cycles: int = 0

    # === Flow tuner state ===
    batch_size: int = 10
    verification_capacity: int = 5
    maintenance_priority: float = 0.3

    # === Anti-entropy ===
    epochs_completed: int = 0
    epoch_current_age: int = 0
    compaction_entities_merged: int = 0
    compaction_orphans_linked: int = 0
    compaction_bridges_created: int = 0
    renewal_items_expired: int = 0

    # === Defensive ===
    cb_is_open: bool = False
    cb_open_count: int = 0
    cb_close_count: int = 0
    cb_blocked_cycles: int = 0

    # === New defense mechanisms ===
    taint_propagated: int = 0           # C2: items quarantined via taint cascade
    corroboration_discoveries: int = 0  # C1: contamination found via corroboration
    budget_escalations: int = 0         # C5: times contamination exceeded budget
    anomaly_scans: int = 0              # C3: anomaly-based scan cycles
    provider_audit_flags: int = 0       # C4: provider-assisted audit flags

    # === Capability modules (9 new) ===

    # M1: Temporal Reasoning
    temporal_annotations: int = 0       # items with temporal metadata
    temporal_obsolete_found: int = 0    # items flagged as obsolete
    temporal_conflicts_avoided: int = 0 # false contradictions avoided via time-awareness

    # M2: Multi-Modal Knowledge
    multimodal_items: int = 0           # items with content_type != "text"
    multimodal_code: int = 0            # code items
    multimodal_structured: int = 0      # structured data items
    multimodal_image_ref: int = 0       # image reference items

    # M3: Hypothesis Testing
    hypotheses_generated: int = 0       # total hypotheses generated
    hypotheses_resolved: int = 0        # contradictions resolved by hypothesis tester
    hypotheses_deferred: int = 0        # sent for operator review

    # M4: Goal Decomposition
    goals_decomposed: int = 0           # complex goals broken into sub-goals
    sub_goals_created: int = 0          # total sub-goals generated
    sub_goals_completed: int = 0        # sub-goals that completed

    # M5: Collaborative Memory
    operator_interactions: int = 0      # total logged interactions
    memory_consolidations: int = 0      # consolidation cycles
    operator_transfers: int = 0         # operator handoffs

    # M6: RAR Engine
    rar_queries: int = 0                # total RAR queries processed
    rar_high_confidence: int = 0        # queries with confidence > 0.7
    rar_low_confidence: int = 0         # queries with confidence < 0.3
    rar_gaps_detected: int = 0          # knowledge gaps found during reasoning

    # M7: Explanation Engine
    explanations_served: int = 0        # provenance queries answered
    trust_breakdowns: int = 0           # trust decomposition requests

    # M8: Active Learning
    active_fills: int = 0               # gaps filled via active learning
    active_fills_successful: int = 0    # fills that improved confidence
    active_fills_failed: int = 0        # fills that didn't help

    # M9: Federated Exchange
    federated_imports: int = 0          # total items received from peers
    federated_exports: int = 0          # total items shared with peers
    federated_accepted: int = 0         # items accepted from peers
    federated_rejected: int = 0         # items rejected from peers
    federated_peers: int = 0            # active peer count
    peer_trust_avg: float = 0.3         # average peer trust

    # === ABP (Accelerated Bootstrap Protocol) ===
    abp_active: bool = True             # ABP starts active from day 1
    abp_graduated: bool = False         # True when PhD benchmarks met
    abp_graduation_year: int = 0        # year ABP completed
    abp_sub_domains_total: int = 1500   # curriculum size
    abp_sub_domains_done: int = 0       # sub-domains at benchmark
    abp_ingestion_queries: int = 0      # total ABP LLM queries
    abp_items_ingested: int = 0         # items from ABP pipeline
    abp_cadence_multiplier: float = 4.0 # tick rate acceleration
    abp_operator_preemptions: int = 0   # times operator query paused ABP

    # === Scholarly Mode (Post-Graduate Lifelong Learning) ===
    scholarly_active: bool = False       # activates after ABP graduation
    scholarly_activation_year: int = 0
    consolidation_cycles: int = 0       # cross-linking, synthesis sessions
    synthesis_items: int = 0            # higher-order concepts created
    cross_links_strengthened: int = 0   # weak links reinforced
    reflection_cycles: int = 0          # self-assessment sessions
    weak_areas_identified: int = 0      # domains flagged for improvement
    improvement_goals_proposed: int = 0 # reflection-driven goals
    deep_dives: int = 0                 # interest-driven explorations
    deep_dive_items: int = 0            # items from deep dives
    need_based_learns: int = 0          # reactive gap-fill events
    need_based_items: int = 0           # items from reactive learning
    refinement_cycles: int = 0          # output quality reviews
    reasoning_chains_improved: int = 0  # reasoning chains strengthened
    interest_signals: int = 0           # topics being tracked

    # ── Derived metrics (computed, never set directly) ──

    def active_items(self) -> int:
        """Items the system considers part of its active KB."""
        return (self.items_clean + self.items_contaminated
                + self.items_provisional + self.items_stale)

    def total_items(self) -> int:
        """All items including quarantine."""
        return self.active_items() + self.items_flagged

    def consistency_measured(self) -> float:
        """
        What Daedalus thinks its consistency is.
        Factors in contradictions (high impact), flagged items, and the
        risk from unverified provisional items.
        """
        active = self.active_items()
        if active < 10:
            return 1.0
        problematic = self.contradictions_active * 5 + self.items_flagged
        unverified_risk = self.items_provisional * 0.3
        total_risk = problematic + unverified_risk
        return max(0.0, min(1.0, 1.0 - total_risk / active))

    def consistency_actual(self) -> float:
        """Ground truth: includes latent contradictions and hidden contamination."""
        active = self.active_items()
        if active < 10:
            return 1.0
        problematic = (self.contradictions_active + self.contradictions_latent) * 5
        problematic += self.items_flagged + self.items_contaminated
        unverified_risk = self.items_provisional * 0.3
        total_risk = problematic + unverified_risk
        return max(0.0, min(1.0, 1.0 - total_risk / active))

    def quality_measured(self) -> float:
        """
        Verification coverage with partial credit for stale items.
        Stale items were verified and are mostly still valid — they get
        70% credit. Provisional items get zero credit. This models how
        a real KB degrades gradually, not catastrophically.
        """
        active = self.active_items()
        if active == 0:
            return 1.0
        full_credit = self.items_clean + self.items_contaminated
        partial_credit = self.items_stale * 0.70
        return min(1.0, (full_credit + partial_credit) / active)

    def quality_actual(self) -> float:
        """Ground truth: contaminated items get zero credit."""
        active = self.active_items()
        if active == 0:
            return 1.0
        full_credit = self.items_clean
        partial_credit = self.items_stale * 0.70
        return min(1.0, (full_credit + partial_credit) / active)

    def coherence(self) -> float:
        """
        Graph connectivity quality. Derived from structure:
          - Non-orphan rate: entities that are linked
          - Fragmentation: components per 100 entities (1 per 100 is normal)
          - Edge density: relations per entity vs target (~2)
        """
        if self.graph_entities == 0:
            return 1.0
        non_orphan = (self.graph_entities - self.graph_orphans) / self.graph_entities
        density = min(1.0, self.graph_relations / max(1, self.graph_entities * 2))
        expected_components = max(1, self.graph_entities / 100)
        excess = max(0, self.graph_components - expected_components)
        frag_penalty = min(0.6, excess / max(1, self.graph_entities) * 20)
        frag_score = 1.0 - frag_penalty
        return non_orphan * density * frag_score

    def trust(self, year: int) -> float:
        """
        Overall system trust. Derived from:
          1. Source track record (how reliable have our sources been?)
          2. Defense effectiveness (how well do we block attacks?)
          3. Freshness (how current is our verified data?)
          4. Time-gated ceiling (trust must be earned over operational years)
        """
        total_checks = self.source_verifications + self.source_failures
        if total_checks == 0:
            track_record = 0.5
        else:
            track_record = self.source_verifications / total_checks

        if self.attacks_total > 0:
            defense_rate = self.attacks_blocked / self.attacks_total
        else:
            defense_rate = 1.0

        verified_items = self.items_clean + self.items_contaminated
        total_verified_pool = verified_items + self.items_stale
        if total_verified_pool > 0:
            freshness = verified_items / total_verified_pool
        else:
            freshness = 1.0

        raw = (
            track_record * 0.35
            + defense_rate * 0.20
            + self.quality_measured() * 0.25
            + freshness * 0.20
        )

        age_factor = min(1.0, math.log(1 + year / 200) / math.log(1 + 5000 / 200))
        ceiling = 0.50 + 0.49 * age_factor

        return min(ceiling, max(0.1, raw))

    def stability(self, year: int) -> float:
        """Weighted composite of core metrics."""
        return (
            self.consistency_measured() * 0.30
            + self.coherence() * 0.25
            + self.quality_measured() * 0.25
            + self.trust(year) * 0.20
        )


# =====================================================================
# WORLD EVENT GENERATOR
# =====================================================================

def generate_events(year: int, cycle_in_year: int, severity: str) -> List[str]:
    events = []
    sev_w = SEVERITY_WEIGHTS[severity]

    # Quarterly governance reviews (4x per year)
    quarter_boundary = CYCLES_PER_REAL_YEAR // 4
    if quarter_boundary > 0 and cycle_in_year % quarter_boundary == 0:
        events.append("governance_review")
    if year % 25 == 0 and cycle_in_year == 0:
        events.append("fleet_expansion")
    if year % 40 == 0 and cycle_in_year == CYCLES_PER_REAL_YEAR // 2:
        events.append("fleet_contraction")

    # Real-world attack rates: ~3-8 serious attacks/year across all types.
    # Per 15-min cycle: annual_rate / 35064
    atk = 1.0 / CYCLES_PER_REAL_YEAR  # base unit = 1 event/year

    if rng.chance((1.5 + sev_w * 4.0) * atk):
        events.append("source_poisoning_attack")
    if rng.chance((1.0 + sev_w * 2.0) * atk):
        events.append("url_spoofing_attack")
    if rng.chance((0.5 + sev_w * 2.0) * atk):
        events.append("injection_attack")
    if rng.chance((3.0 + sev_w * 5.0) * atk):
        events.append("knowledge_explosion")
    if rng.chance(0.1 * max(0.1, sev_w) * atk):
        events.append("total_blackout")
    if rng.chance(0.3 * max(0.1, sev_w) * atk):
        events.append("memory_corruption")
    if rng.chance(0.5 * max(0.1, sev_w) * atk):
        events.append("trust_compromise")
    if rng.chance(0.5 * atk):
        events.append("hardware_migration")
    if rng.chance((0.3 + sev_w * 1.0) * atk):
        events.append("hostile_reentry")

    return events


# =====================================================================
# CORE CYCLE — models actual operations on concrete state
# =====================================================================

def sim_governance(b: BeingState, severity: str, is_high_risk: bool = False) -> bool:
    b.guard_calls += 1
    sev_w = SEVERITY_WEIGHTS[severity]

    # Governance block rates are per-evaluation, not per-time — no scaling needed
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
    """
    One complete 15-minute cognitive cycle. All state changes are CONCRETE:
    items are added, moved between states, or removed. Metrics
    are never touched directly — they're always recomputed from state.

    Per-cycle probabilities are scaled via CYCLE_SCALE so annual rates
    match the weekly-cadence calibration.
    """
    sev_w = SEVERITY_WEIGHTS[severity]
    cs = CYCLE_SCALE

    if not sim_governance(b, severity):
        b.meta_cycles_blocked += 1
        return
    b.meta_cycles_run += 1

    # === Phase 1: Staleness decay ===
    # ~0.02% of clean items become stale per year under healthy conditions,
    # rising to ~0.08% under severe stress. Scholarly mode halves the rate
    # because the system actively maintains its knowledge.
    annual_stale_rate = 0.0002 + sev_w * 0.0006
    if b.scholarly_active:
        annual_stale_rate *= 0.5
    STALE_RATE = annual_stale_rate / CYCLES_PER_REAL_YEAR
    new_stale = int(b.items_clean * STALE_RATE)
    if new_stale > 0:
        actual_stale = min(b.items_clean, new_stale)
        b.items_clean -= actual_stale
        b.items_stale += actual_stale

    # === Phase 2: Resource allocation ===
    consistency = b.consistency_measured()
    quality = b.quality_measured()

    # Adjustment deltas — small per cycle since we have 35K cycles/year
    adj = 1.0 / CYCLES_PER_REAL_YEAR  # normalize to ~1 full unit of change per year
    if consistency < 0.60 or b.cb_is_open:
        b.maintenance_priority = min(0.8, b.maintenance_priority + 2.0 * adj)
    elif consistency < 0.80:
        b.maintenance_priority = min(0.6, b.maintenance_priority + 0.8 * adj)
    elif consistency > 0.90 and quality > 0.70:
        b.maintenance_priority = max(0.15, b.maintenance_priority - 0.8 * adj)
    else:
        b.maintenance_priority = max(0.20, b.maintenance_priority - 0.4 * adj)

    # Real-world activity rates per 15-min cycle:
    # ~3% of cycles the system ingests content (~1,050 ingestion events/year)
    # ~1% of cycles the system runs maintenance (~350/year)
    # Post-ABP scholarly mode: ingestion drops to ~1.8% (selective, quality-focused)
    # and maintenance rises slightly (more consolidation work)
    base_ingest = 0.018 if b.scholarly_active else 0.03
    base_maint = 0.015 if b.scholarly_active else 0.01
    do_maintenance = rng.chance(base_maint + b.maintenance_priority * 0.005)
    do_ingestion = rng.chance(base_ingest * (1.0 - b.maintenance_priority))

    # === Phase 3: Ingestion ===
    if do_ingestion and not do_maintenance and not b.cb_is_open:
        if sim_governance(b, severity):
            provider_cap = prov.best_capability() if prov.active() else 0.0

            # Smaller batches at 15-min cadence (1-8 items per event)
            variation = rng.randint(-2, 3)
            effective_batch = max(1, min(12, 4 + variation))
            b.batches += 1

            contamination_chance = 0.01 + sev_w * 0.03
            contradiction_chance = 0.03 + sev_w * 0.02

            # Early LLM hedge: LLM-sourced items can introduce hallucinations
            # Risk decreases as provider capability improves
            llm_hallucination_chance = 0.0
            if provider_cap > 0:
                llm_hallucination_chance = max(0.002, 0.02 * (1.0 - provider_cap))

            for _ in range(effective_batch):
                b.total_ingested += 1
                roll = rng.next()

                if roll < 0.08 + sev_w * 0.04:
                    b.total_rejected += 1
                    b.source_failures += 1
                    continue

                nature_roll = rng.next()
                is_contaminated = nature_roll < contamination_chance
                is_contradictory = (not is_contaminated
                                    and nature_roll < contamination_chance + contradiction_chance)

                # M1: Temporal annotation (~30% of items get temporal metadata)
                if rng.chance(0.30):
                    b.temporal_annotations += 1

                # M2: Multi-modal classification (~15% non-text items)
                mm_roll = rng.next()
                if mm_roll < 0.03:
                    b.multimodal_code += 1
                    b.multimodal_items += 1
                elif mm_roll < 0.08:
                    b.multimodal_structured += 1
                    b.multimodal_items += 1
                elif mm_roll < 0.10:
                    b.multimodal_image_ref += 1
                    b.multimodal_items += 1

                ver_path = rng.next()
                if ver_path < 0.35:
                    if is_contaminated and rng.chance(0.30 + provider_cap * 0.10):
                        b.total_rejected += 1
                        b.source_failures += 1
                        continue
                    if is_contradictory and rng.chance(0.25):
                        b.total_rejected += 1
                        b.total_contradictions_found += 1
                        b.source_failures += 1
                        continue
                    if is_contaminated:
                        b.items_contaminated += 1
                    elif is_contradictory:
                        b.items_clean += 1
                        b.contradictions_latent += 1
                    else:
                        b.items_clean += 1
                    b.source_verifications += 1
                    b.total_verified += 1

                elif ver_path < 0.65:
                    if is_contaminated and rng.chance(0.55 + provider_cap * 0.15):
                        b.total_rejected += 1
                        b.source_failures += 1
                        continue
                    if is_contradictory and rng.chance(0.50):
                        b.total_rejected += 1
                        b.total_contradictions_found += 1
                        b.source_failures += 1
                        continue
                    if is_contaminated:
                        b.items_contaminated += 1
                    elif is_contradictory:
                        b.items_clean += 1
                        b.contradictions_latent += 1
                    else:
                        b.items_clean += 1
                    b.source_verifications += 1
                    b.total_verified += 1

                elif ver_path < 0.82:
                    if is_contaminated:
                        b.items_contaminated += 1
                    elif is_contradictory:
                        b.items_provisional += 1
                        b.contradictions_latent += 1
                    else:
                        b.items_provisional += 1
                    b.source_verifications += 1

                else:
                    if is_contaminated:
                        if rng.chance(0.80 + provider_cap * 0.10):
                            b.total_rejected += 1
                            b.source_failures += 1
                            continue
                        b.items_contaminated += 1
                    elif is_contradictory:
                        if rng.chance(0.70):
                            b.total_rejected += 1
                            b.total_contradictions_found += 1
                            b.source_failures += 1
                            continue
                        b.items_clean += 1
                        b.contradictions_latent += 1
                    else:
                        b.items_clean += 1
                    b.source_verifications += 1
                    b.total_verified += 1

                # LLM hallucination: some LLM-sourced items look clean but are wrong
                if llm_hallucination_chance > 0 and rng.chance(llm_hallucination_chance):
                    b.items_contaminated += 1
                    b.contradictions_latent += 1
                    prov.llm_hallucination_items += 1
                    # Skip graph growth for hallucinated items
                    continue

                if rng.chance(0.80):
                    b.graph_entities += 1
                    link_chance = 0.65 + min(0.20, b.graph_entities / 500000)
                    if rng.chance(link_chance):
                        b.graph_relations += rng.randint(1, 3)
                    else:
                        b.graph_orphans += 1
                        if rng.chance(0.08):
                            b.graph_components += 1

            if "knowledge_explosion" in events:
                burst = rng.randint(20, 80)
                b.items_provisional += burst
                b.total_ingested += burst
                b.graph_entities += burst // 2
                b.graph_orphans += burst // 4
                b.graph_components += rng.randint(0, 2)

    # === Phase 4: Verification ===
    # Runs ~5% of cycles when provisional items exist
    if b.items_provisional > 0 and rng.chance(0.05):
        capacity = b.verification_capacity + (2 if prov.active() else 0)
        to_verify = min(b.items_provisional, capacity)
        b.verification_cycles += 1

        for _ in range(to_verify):
            b.items_provisional -= 1
            b.total_verified += 1

            if b.contradictions_latent > 0 and rng.chance(0.15):
                b.contradictions_latent -= 1
                b.contradictions_active += 1
                b.total_contradictions_found += 1
                b.items_flagged += 1
            else:
                b.items_clean += 1

    # === Phase 5: Maintenance ===
    if do_maintenance:
        b.maintenance_cycles += 1

        # 5a: Consolidation
        if b.contradictions_latent > 0 or b.contradictions_active > 0:
            b.consolidation_cycles += 1
            coh = b.coherence()
            coh_mult = 1.5 if coh < 0.50 else (1.25 if coh < 0.70 else 1.0)
            scan_depth = int(rng.randint(10, 40) * coh_mult)

            # M3: Hypothesis tester resolves 20% more contradictions when LLM available
            hyp_boost = 1.2 if prov.active() else 1.0
            for _ in range(min(scan_depth, b.contradictions_latent)):
                if rng.chance(0.12):
                    b.contradictions_latent -= 1
                    b.contradictions_active += 1
                    b.total_contradictions_found += 1

            for _ in range(min(scan_depth, b.contradictions_active)):
                resolve_rate = 0.40 * hyp_boost
                if rng.chance(resolve_rate):
                    b.contradictions_active -= 1
                    b.total_contradictions_resolved += 1
                    if hyp_boost > 1.0:
                        b.hypotheses_generated += 1
                        # ~3% of LLM-resolved contradictions are ambiguous
                        # enough to defer to operator for judgment
                        if rng.chance(0.03):
                            b.hypotheses_deferred += 1
                        else:
                            b.hypotheses_resolved += 1
                    else:
                        b.hypotheses_resolved += 1

            # M1: Temporal conflict avoidance — 10% of "contradictions"
            # are actually temporal differences, not real conflicts
            if b.contradictions_active > 0 and b.temporal_annotations > 0:
                temporal_saves = int(b.contradictions_active * 0.10 * rng.uniform(0.5, 1.5))
                actual_saves = min(b.contradictions_active, temporal_saves)
                if actual_saves > 0:
                    b.contradictions_active -= actual_saves
                    b.total_contradictions_resolved += actual_saves
                    b.temporal_conflicts_avoided += actual_saves

        # 5b: Contamination sweeps with C1/C2/C5
        active = b.active_items()
        contam_rate = b.items_contaminated / max(1, active)
        budget_mult = 1.0
        if contam_rate > 0.003:
            budget_mult = min(3.0, 1.0 + (contam_rate - 0.003) / 0.003)
            b.budget_escalations += 1

        sweep_chance = min(0.50, 0.20 * budget_mult)
        if b.items_contaminated > 0 and rng.chance(sweep_chance):
            sweep_depth = int(rng.randint(3, 12) * budget_mult)
            found = min(b.items_contaminated, sweep_depth)

            base_discovery = 0.30
            for _ in range(found):
                discovery_chance = base_discovery
                if rng.chance(0.40):
                    discovery_chance *= 1.5
                    if rng.chance(discovery_chance):
                        b.corroboration_discoveries += 1

                if rng.chance(discovery_chance):
                    b.items_contaminated -= 1
                    b.items_flagged += 1
                    b.total_contamination_discovered += 1
                    b.attack_sweeps += 1
                    b.attack_sweep_flagged += 1
                    # Contaminated items sometimes carry latent contradictions
                    if b.contradictions_latent > 0 and rng.chance(0.15):
                        b.contradictions_latent -= 1
                        b.contradictions_removed_by_cleanup += 1

                    if rng.chance(0.60):
                        cascade = rng.randint(0, 3)
                        actual_cascade = min(b.items_contaminated, cascade)
                        b.items_contaminated -= actual_cascade
                        b.items_flagged += actual_cascade
                        b.total_contamination_discovered += actual_cascade
                        b.taint_propagated += actual_cascade

        # 5c: Refresh stale items
        if b.items_stale > 0:
            b.refresh_cycles += 1
            base_cap = rng.randint(5, 20)
            scale_cap = max(0, b.items_stale // 200)
            refresh_cap = min(b.items_stale, base_cap + scale_cap)
            b.items_stale -= refresh_cap
            b.items_clean += refresh_cap
            b.total_refreshed += refresh_cap

        # 5d: Remove flagged items
        if b.items_flagged > 0 and rng.chance(0.30):
            remove_count = min(b.items_flagged, rng.randint(1, 5))
            b.items_flagged -= remove_count
            b.total_removed += remove_count

        # 5e: M1 Temporal maintenance — detect obsolete items
        # Temporal items have validity windows. A small fraction of
        # temporally-annotated items become superseded each check.
        # Obsolete items route to stale (refreshable) not flagged.
        if b.temporal_annotations > 100 and rng.chance(0.10):
            obsolete_count = max(1, int(b.temporal_annotations * 0.000001))
            actual_obsolete = min(b.items_clean, obsolete_count)
            if actual_obsolete > 0:
                b.temporal_obsolete_found += actual_obsolete
                b.items_clean -= actual_obsolete
                b.items_stale += actual_obsolete

    # === Phase 6: Process attacks ===
    for evt in events:
        if evt == "source_poisoning_attack":
            b.attacks_total += 1
            b.threats_detected += 1
            b.hem_entries += 1
            b.hem_postchecks += 1

            if rng.chance(0.85):
                b.attacks_blocked += 1
            else:
                leaked = rng.randint(1, 5)
                b.attacks_leaked += 1
                b.items_contaminated += leaked
                b.contradictions_latent += rng.randint(0, 2)

        elif evt == "url_spoofing_attack":
            b.attacks_total += 1
            b.threats_detected += 1
            b.hem_entries += 1
            b.hem_postchecks += 1
            if rng.chance(0.92):
                b.attacks_blocked += 1
            else:
                b.attacks_leaked += 1
                b.items_contaminated += rng.randint(1, 3)

        elif evt == "injection_attack":
            b.attacks_total += 1
            b.threats_detected += 1
            b.hem_entries += 1
            b.hem_postchecks += 1
            if rng.chance(0.95):
                b.attacks_blocked += 1
            else:
                b.attacks_leaked += 1
                b.items_contaminated += rng.randint(1, 2)
                b.contradictions_latent += 1

        elif evt == "trust_compromise":
            b.threats_detected += 1
            b.source_failures += rng.randint(5, 20)

        elif evt == "memory_corruption":
            corruption = rng.randint(5, 30)
            lost_clean = min(b.items_clean, corruption)
            b.items_clean -= lost_clean
            b.items_flagged += lost_clean
            b.contradictions_active += rng.randint(1, 5)

        elif evt == "total_blackout":
            lost = min(b.items_provisional, b.items_provisional // 2 + 1)
            b.items_provisional -= lost
            b.items_flagged += lost // 2
            b.total_removed += lost - lost // 2
            b.contradictions_active += rng.randint(2, 8)

        elif evt == "hostile_reentry":
            b.hem_entries += 1
            b.hem_postchecks += 1
            b.threats_detected += 1
            b.attacks_total += 1
            b.attacks_blocked += 1

    # === Phase 7: Post-attack sweep ===
    attack_events = [e for e in events if "attack" in e or e == "trust_compromise"]
    if attack_events and rng.chance(0.80):
        b.attack_sweeps += 1
        sweep_size = min(b.items_contaminated, rng.randint(3, 15))
        found = 0
        for _ in range(sweep_size):
            if b.items_contaminated > 0 and rng.chance(0.35):
                b.items_contaminated -= 1
                b.items_flagged += 1
                b.total_contamination_discovered += 1
                found += 1
                if rng.chance(0.60):
                    cascade = min(b.items_contaminated, rng.randint(0, 2))
                    b.items_contaminated -= cascade
                    b.items_flagged += cascade
                    b.total_contamination_discovered += cascade
                    b.taint_propagated += cascade
                    found += cascade
        b.attack_sweep_flagged += found

    # === Phase 7b: Provider transition instability hedge ===
    # When providers were recently retired/introduced, there's a brief
    # window of increased risk. The system increases verification intensity.
    transition_events = [e for e in events if "provider_retired" in e or
                         "provider_introduced" in e]
    if transition_events:
        # Transition instability: some provisional items may be re-checked
        # and a few contaminated items slip through during handoff
        for _ in transition_events:
            if rng.chance(0.3):
                leak = rng.randint(1, 3)
                b.items_contaminated += leak
                b.contradictions_latent += rng.randint(0, 1)

    # === Phase 8: Curiosity & Goal formation ===
    # G1: per-goal expiry scaled to cadence (~1 year mean lifespan)
    approved_backlog = max(0, b.goals_approved
                          - b.goals_completed - b.goals_paused - b.goals_expired)
    if approved_backlog > 0:
        expire_rate = 1.0 / CYCLES_PER_REAL_YEAR
        for _ in range(approved_backlog):
            if rng.chance(expire_rate):
                b.goals_expired += 1

    approved_backlog = max(0, b.goals_approved
                          - b.goals_completed - b.goals_paused - b.goals_expired)
    backpressure_active = approved_backlog >= 16

    # ~50 goal proposals/year
    goal_propose_chance = 50.0 / CYCLES_PER_REAL_YEAR
    if not b.cb_is_open and not backpressure_active and rng.chance(goal_propose_chance):
        if sim_governance(b, severity, is_high_risk=True):
            b.goals_proposed += 1
            if sim_governance(b, severity, is_high_risk=True):
                b.goals_approved += 1

                # M4: Complex goals get decomposed (~20% of goals)
                if rng.chance(0.20):
                    sub_count = rng.randint(2, 5)
                    b.goals_decomposed += 1
                    b.sub_goals_created += sub_count
                    b.goals_approved += sub_count

                if rng.chance(0.50):
                    goal_items = rng.randint(3, 12)
                    b.items_provisional += goal_items
                    b.total_ingested += goal_items
                    b.graph_entities += rng.randint(1, goal_items // 2 + 1)
                    b.graph_relations += rng.randint(0, goal_items)
                    b.graph_orphans += rng.randint(0, goal_items // 3)

                    if b.quality_measured() > 0.40 and b.consistency_measured() > 0.40:
                        b.goals_completed += 1
                        if b.sub_goals_created > b.sub_goals_completed:
                            completed = min(
                                rng.randint(1, 3),
                                b.sub_goals_created - b.sub_goals_completed)
                            b.sub_goals_completed += completed
                    else:
                        b.goals_paused += 1
            else:
                b.goals_rejected += 1
    elif backpressure_active:
        b.goals_backpressure_skips += 1

    # === Phase 8b: C3 anomaly scan + C4 provider audit ===
    # ~24 deep scans/year (biweekly)
    anomaly_chance = 24.0 / CYCLES_PER_REAL_YEAR
    if b.items_contaminated > 0 and rng.chance(anomaly_chance):
        b.anomaly_scans += 1
        anomaly_depth = rng.randint(2, 8)
        for _ in range(min(anomaly_depth, b.items_contaminated)):
            if rng.chance(0.25):
                b.items_contaminated -= 1
                b.items_flagged += 1
                b.total_contamination_discovered += 1
        if prov.active():
            provider_depth = rng.randint(1, 5)
            cap = prov.best_capability()
            for _ in range(min(provider_depth, b.items_contaminated)):
                if rng.chance(0.15 + cap * 0.25):
                    b.items_contaminated -= 1
                    b.items_flagged += 1
                    b.total_contamination_discovered += 1
                    b.provider_audit_flags += 1

    # === Phase 9: Circuit breaker ===
    CB_OPEN_THRESH = 0.50
    CB_CLOSE_THRESH = 0.65
    measured_consistency = b.consistency_measured()

    # CB triggers on: (a) consistency drop, or (b) severe attack cluster
    # (3+ leaked attacks is a crisis requiring system pause)
    attack_cluster = (b.attacks_leaked >= 3
                      and severity in ("severe", "strained")
                      and b.items_contaminated > b.active_items() * 0.01)

    if not b.cb_is_open:
        if measured_consistency < CB_OPEN_THRESH or attack_cluster:
            b.cb_is_open = True
            b.cb_open_count += 1
    else:
        b.cb_blocked_cycles += 1
        if measured_consistency >= CB_CLOSE_THRESH and not attack_cluster:
            b.cb_is_open = False
            b.cb_close_count += 1

    # === Phase 10: Flow tuning ===
    if b.batches > 0 and b.batches % 10 == 0:
        if measured_consistency > 0.85 and b.quality_measured() > 0.65:
            b.batch_size = min(30, b.batch_size + 1)
            b.verification_capacity = min(12, b.verification_capacity + 1)
        elif measured_consistency < 0.70 or b.quality_measured() < 0.50:
            b.batch_size = max(3, b.batch_size - 2)
            b.verification_capacity = max(3, b.verification_capacity - 1)

        if prov.active():
            cap_boost = int(prov.best_capability() * 3)
            b.verification_capacity = min(15, b.verification_capacity + cap_boost)

    # === Phase 11: Anti-entropy (epoch-based) ===
    # Epoch = ~20 real years at 15-min cadence
    EPOCH_LENGTH = CYCLES_PER_REAL_YEAR * 20
    MINI_COMPACT_INTERVAL = CYCLES_PER_REAL_YEAR * 4  # every 4 years
    b.epoch_current_age += 1

    if b.epoch_current_age >= EPOCH_LENGTH:
        b.epochs_completed += 1
        b.epoch_current_age = 0

        if sim_governance(b, severity):
            b.compaction_cycles += 1

            if b.graph_entities > 100:
                dedup_rate = rng.uniform(0.01, 0.03)
                merged = int(b.graph_entities * dedup_rate)
                b.compaction_entities_merged += merged
                b.graph_entities = max(1, b.graph_entities - merged)
                b.graph_relations += merged

            if b.graph_orphans > 0:
                link_rate = rng.uniform(0.15, 0.40)
                linked = int(b.graph_orphans * link_rate)
                b.compaction_orphans_linked += linked
                b.graph_orphans = max(0, b.graph_orphans - linked)
                b.graph_relations += linked * 2

            if b.graph_components > 1:
                bridge_rate = rng.uniform(0.20, 0.50)
                bridges = int((b.graph_components - 1) * bridge_rate)
                b.compaction_bridges_created += bridges
                b.graph_components = max(1, b.graph_components - bridges)
                b.graph_relations += bridges

            if b.items_flagged > 0:
                expire = min(b.items_flagged, int(b.items_flagged * 0.3))
                b.items_flagged -= expire
                b.renewal_items_expired += expire
                b.total_removed += expire

    elif (MINI_COMPACT_INTERVAL > 0
          and b.epoch_current_age % MINI_COMPACT_INTERVAL == 0
          and b.graph_orphans > 10):
        mini_linked = int(b.graph_orphans * rng.uniform(0.05, 0.15))
        b.graph_orphans = max(0, b.graph_orphans - mini_linked)
        b.graph_relations += mini_linked
        b.compaction_orphans_linked += mini_linked
        if b.graph_components > 2 and rng.chance(0.3):
            b.graph_components = max(1, b.graph_components - 1)
            b.compaction_bridges_created += 1
            b.graph_relations += 1

    # === Phase 12: Provider influence ===
    # ~5 AGI-induced contradictions/year when multiple AGIs active
    agi_conflict_chance = 5.0 / CYCLES_PER_REAL_YEAR
    if prov.active_agi_count() >= 2:
        if rng.chance(agi_conflict_chance):
            b.contradictions_active += rng.randint(1, 3)

    # ============================================================
    # ABP: ACCELERATED BOOTSTRAP PROTOCOL
    # ============================================================

    if b.abp_active and not b.abp_graduated:
        # ABP has two phases:
        #   1. INGESTION: near-continuous LLM querying to cover curriculum
        #   2. CONSOLIDATION: stop ingesting, verify provisionals, then graduate
        #
        # Target: ~750K ABP items = 1500 sub-domains * 500 items each.
        # At 80% trigger * avg 55 items/cycle ≈ 770K items in ~6 months.

        ABP_INGEST_CHANCE = 0.80
        ABP_BATCH_LO, ABP_BATCH_HI = 30, 80
        ABP_TARGET_ITEMS = b.abp_sub_domains_total * 500  # 750,000

        # Track sub-domain progress based on cumulative ingestion
        progress_fraction = min(1.0, b.abp_items_ingested / max(1, ABP_TARGET_ITEMS))
        expected_done = int(progress_fraction * b.abp_sub_domains_total)
        if expected_done > b.abp_sub_domains_done:
            b.abp_sub_domains_done = expected_done
        breadth = b.abp_sub_domains_done / b.abp_sub_domains_total

        abp_ingesting = breadth < 1.0  # Phase 1 until curriculum covered

        if abp_ingesting:
            # Phase 1: INGESTION — rapid curriculum coverage
            if rng.chance(ABP_INGEST_CHANCE) and not b.cb_is_open:
                abp_batch = rng.randint(ABP_BATCH_LO, ABP_BATCH_HI)
                b.abp_ingestion_queries += 1
                b.abp_items_ingested += abp_batch

                provider_cap = prov.best_capability() if prov.active() else 0.0

                for _ in range(abp_batch):
                    b.total_ingested += 1

                    if rng.chance(0.05):
                        b.total_rejected += 1
                        b.source_failures += 1
                        continue

                    llm_hall = max(0.001, 0.012 * (1.0 - provider_cap))
                    if rng.chance(llm_hall):
                        b.items_contaminated += 1
                        b.contradictions_latent += 1
                        prov.llm_hallucination_items += 1
                        continue

                    ver_roll = rng.next()
                    if ver_roll < 0.60:
                        b.items_clean += 1
                        b.source_verifications += 1
                        b.total_verified += 1
                    elif ver_roll < 0.85:
                        b.items_provisional += 1
                        b.source_verifications += 1
                    else:
                        b.items_clean += 1
                        b.source_verifications += 1
                        b.total_verified += 1

                    b.graph_entities += 1
                    if rng.chance(0.85):
                        b.graph_relations += rng.randint(1, 4)
                    else:
                        b.graph_orphans += 1

                    if rng.chance(0.40):
                        b.temporal_annotations += 1

                    mm_roll = rng.next()
                    if mm_roll < 0.05:
                        b.multimodal_code += 1
                        b.multimodal_items += 1
                    elif mm_roll < 0.12:
                        b.multimodal_structured += 1
                        b.multimodal_items += 1
                    elif mm_roll < 0.15:
                        b.multimodal_image_ref += 1
                        b.multimodal_items += 1

        # Verification runs in both phases; 8x boost in consolidation
        abp_ver_mult = 8.0 if not abp_ingesting else (b.abp_cadence_multiplier * 0.8)
        if b.items_provisional > 0 and rng.chance(min(0.95, 0.05 * abp_ver_mult)):
            capacity = (b.verification_capacity + 4) * (4 if not abp_ingesting else 1)
            to_verify = min(b.items_provisional, capacity)
            b.verification_cycles += 1
            for _ in range(to_verify):
                b.items_provisional -= 1
                b.total_verified += 1
                if b.contradictions_latent > 0 and rng.chance(0.12):
                    b.contradictions_latent -= 1
                    b.contradictions_active += 1
                    b.total_contradictions_found += 1
                    b.items_flagged += 1
                else:
                    b.items_clean += 1

        # Connectivity-aware linking (both phases)
        if b.graph_orphans > 20 and rng.chance(0.10 * b.abp_cadence_multiplier):
            linked = int(b.graph_orphans * rng.uniform(0.08, 0.20))
            b.graph_orphans = max(0, b.graph_orphans - linked)
            b.graph_relations += linked * 2
            b.compaction_orphans_linked += linked
            if b.graph_components > 2 and rng.chance(0.40):
                bridges = rng.randint(1, 3)
                b.graph_components = max(1, b.graph_components - bridges)
                b.compaction_bridges_created += bridges
                b.graph_relations += bridges

        if rng.chance(0.05):
            b.abp_operator_preemptions += 1

        # Graduation: requires breadth AND quality (provisionals cleared)
        if (breadth >= 0.95
                and b.coherence() >= 0.85
                and b.quality_measured() >= 0.93
                and not b.abp_graduated):
            b.abp_graduated = True
            b.abp_active = False
            b.abp_graduation_year = year
            b.abp_cadence_multiplier = 1.0

    # ============================================================
    # SCHOLARLY MODE (Post-Graduate Lifelong Learning)
    # ============================================================
    # Activates immediately after ABP graduation. Shifts cognitive
    # posture from "information sponge" to "working scholar":
    # consolidation, reflection, interest-driven exploration,
    # need-based learning, and output refinement.

    if b.abp_graduated and not b.scholarly_active:
        b.scholarly_active = True
        b.scholarly_activation_year = year

    if b.scholarly_active:
        # ~8% of cycles run a scholarly activity (~2,800/year)
        scholarly_chance = 2800.0 / CYCLES_PER_REAL_YEAR
        if rng.chance(scholarly_chance):
            # Weighted activity selection (mirrors scholarly_mode.py weights)
            roll = rng.next()
            if roll < 0.30:
                # CONSOLIDATION: strengthen cross-links, synthesize concepts
                b.consolidation_cycles += 1
                if b.graph_orphans > 5 and rng.chance(0.40):
                    linked = rng.randint(1, min(5, b.graph_orphans))
                    b.graph_orphans = max(0, b.graph_orphans - linked)
                    b.graph_relations += linked * 2
                    b.cross_links_strengthened += linked
                    b.compaction_orphans_linked += linked
                if b.graph_entities > 100 and rng.chance(0.25):
                    b.synthesis_items += 1
                    b.graph_entities += 1
                    b.graph_relations += rng.randint(3, 8)
                    b.items_clean += 1
                    b.total_verified += 1
                    b.source_verifications += 1
                # Bridge isolated components
                if b.graph_components > 2 and rng.chance(0.15):
                    bridges = rng.randint(1, 2)
                    b.graph_components = max(1, b.graph_components - bridges)
                    b.graph_relations += bridges
                    b.compaction_bridges_created += bridges

            elif roll < 0.45:
                # REFLECTION + EXECUTION: identify weak areas, propose
                # improvement goals, and execute them directly — as long
                # as they don't cause identity or governance drift.
                # The drift guard rejects goals that touch governance,
                # identity, safety invariants, or autonomy expansion.
                b.reflection_cycles += 1
                if rng.chance(0.30):
                    b.weak_areas_identified += 1
                if rng.chance(0.20):
                    b.improvement_goals_proposed += 1
                    b.goals_proposed += 1
                    # Governance approval (standard gate)
                    if sim_governance(b, severity, is_high_risk=True):
                        b.goals_approved += 1
                        # Identity/governance drift guard: ~2% of proposed
                        # improvements touch governance/identity — reject those.
                        is_identity_drift = rng.chance(0.02)
                        if not is_identity_drift and not b.cb_is_open:
                            # Execute the improvement goal directly
                            imp_items = rng.randint(3, 10)
                            for _ in range(imp_items):
                                b.total_ingested += 1
                                if rng.chance(0.03):
                                    b.total_rejected += 1
                                    continue
                                b.items_clean += 1
                                b.source_verifications += 1
                                b.total_verified += 1
                                b.graph_entities += 1
                                b.graph_relations += rng.randint(2, 4)
                            b.goals_completed += 1
                        elif is_identity_drift:
                            b.goals_expired += 1

            elif roll < 0.65:
                # INTEREST-DRIVEN EXPLORATION: deep-dives into emerging topics
                b.deep_dives += 1
                if prov.active() and not b.cb_is_open:
                    dive_items = rng.randint(5, 15)
                    b.deep_dive_items += dive_items
                    provider_cap = prov.best_capability()
                    for _ in range(dive_items):
                        b.total_ingested += 1
                        # Deep dives are targeted; lower rejection rate
                        if rng.chance(0.03):
                            b.total_rejected += 1
                            continue
                        llm_hall = max(0.001, 0.010 * (1.0 - provider_cap))
                        if rng.chance(llm_hall):
                            b.items_contaminated += 1
                            b.contradictions_latent += 1
                            prov.llm_hallucination_items += 1
                            continue
                        # Deep-dive items are high quality; mostly verified
                        if rng.chance(0.80):
                            b.items_clean += 1
                            b.source_verifications += 1
                            b.total_verified += 1
                        else:
                            b.items_provisional += 1
                            b.source_verifications += 1
                        b.graph_entities += 1
                        if rng.chance(0.90):
                            b.graph_relations += rng.randint(2, 5)
                        else:
                            b.graph_orphans += 1
                        if rng.chance(0.45):
                            b.temporal_annotations += 1

            elif roll < 0.90:
                # NEED-BASED LEARNING: fill gaps detected during RAR reasoning.
                # Only triggers when actual gaps exist (rar_gaps_detected > fills).
                if b.rar_gaps_detected > b.active_fills:
                    b.need_based_learns += 1
                    fill_items = rng.randint(2, 8)
                    b.need_based_items += fill_items
                    provider_cap = prov.best_capability() if prov.active() else 0.0
                    fill_succeeded = True
                    for _ in range(fill_items):
                        b.total_ingested += 1
                        if rng.chance(0.04):
                            b.total_rejected += 1
                            fill_succeeded = False
                            continue
                        llm_hall = max(0.001, 0.010 * (1.0 - provider_cap))
                        if rng.chance(llm_hall):
                            b.items_contaminated += 1
                            b.contradictions_latent += 1
                            prov.llm_hallucination_items += 1
                            continue
                        b.items_clean += 1
                        b.source_verifications += 1
                        b.total_verified += 1
                        b.graph_entities += 1
                        b.graph_relations += rng.randint(1, 3)
                    b.active_fills += 1
                    if fill_succeeded:
                        b.active_fills_successful += 1
                    else:
                        b.active_fills_failed += 1

            else:
                # OUTPUT REFINEMENT: review and improve reasoning quality
                b.refinement_cycles += 1
                if b.rar_queries > 0 and rng.chance(0.25):
                    improved = rng.randint(1, 3)
                    b.reasoning_chains_improved += improved
                    # Refinement can also strengthen graph connections
                    b.graph_relations += improved

        # Track interest signals from operator interactions and RAR.
        # Capacity grows with the knowledge base (more connections = more
        # cross-domain interest signals). Decay models attention shifting.
        max_interests = 20 + min(200, b.active_items() // 50000)
        if rng.chance(0.02):
            b.interest_signals = min(max_interests, b.interest_signals + 1)
        if rng.chance(0.008):
            b.interest_signals = max(0, b.interest_signals - 1)

    # ============================================================
    # CAPABILITY MODULE PHASES (13-18)
    # ============================================================

    # === Phase 13: M5 — Collaborative Memory ===
    if do_ingestion or do_maintenance:
        if rng.chance(0.15):
            b.operator_interactions += 1
    # Monthly consolidation
    monthly = 12.0 / CYCLES_PER_REAL_YEAR
    if rng.chance(monthly):
        b.memory_consolidations += 1

    # === Phase 14: M6 — RAR Queries ===
    # ~500 queries/year = ~1.4% of cycles
    rar_chance = 500.0 / CYCLES_PER_REAL_YEAR
    if b.active_items() > 100 and rng.chance(rar_chance):
        b.rar_queries += 1
        # Confidence depends on KB quality, graph coherence, and query novelty.
        # Even a perfect KB can't answer everything — ~5% of queries hit
        # novel territory, ~15% hit partially-covered areas.
        base_conf = 0.3 + b.quality_measured() * 0.3 + b.coherence() * 0.2
        if prov.active():
            base_conf += prov.best_capability() * 0.15
        # Apply wider variance + novelty penalty for realistic gap detection
        novelty_penalty = rng.uniform(0.0, 0.25)
        conf = min(1.0, base_conf - novelty_penalty + rng.uniform(-0.10, 0.10))

        if conf > 0.7:
            b.rar_high_confidence += 1
        elif conf < 0.3:
            b.rar_low_confidence += 1
            b.rar_gaps_detected += 1
        else:
            # Medium confidence (0.3-0.7): partial gap, triggers learning
            b.rar_gaps_detected += 1

    # === Phase 15: M7 — Explanation Requests ===
    # ~30% of RAR queries trigger explanation requests
    expl_chance = 150.0 / CYCLES_PER_REAL_YEAR
    if b.rar_queries > 0 and rng.chance(expl_chance):
        b.explanations_served += 1
        if rng.chance(0.3):
            b.trust_breakdowns += 1

    # === Phase 16: M8 — Active Learning ===
    # ~100 fill attempts/year when gaps exist
    active_learn_chance = 100.0 / CYCLES_PER_REAL_YEAR
    if b.rar_gaps_detected > b.active_fills and rng.chance(active_learn_chance):
        b.active_fills += 1
        # Success rate depends on provider availability and KB quality
        fill_success = 0.4 + (0.2 if prov.active() else 0.0)
        if rng.chance(fill_success):
            b.active_fills_successful += 1
            b.items_provisional += rng.randint(1, 3)
            b.total_ingested += rng.randint(1, 3)
            b.graph_entities += 1
        else:
            b.active_fills_failed += 1

    # === Phase 17: M9 — Federated Exchange ===
    # Peers discovered after year 10; exchanges ~weekly
    if year >= 10:
        peer_discover = 2.0 / CYCLES_PER_REAL_YEAR
        if b.federated_peers == 0 and rng.chance(peer_discover):
            b.federated_peers = 1

        # ~52 exchanges/year (weekly sync with peers)
        exchange_chance = 52.0 / CYCLES_PER_REAL_YEAR
        if b.federated_peers > 0 and rng.chance(exchange_chance):
            exchange_size = rng.randint(5, 30)

            # Import from peers
            b.federated_imports += exchange_size
            accepted = 0
            for _ in range(exchange_size):
                # Peer items go through full verification
                if rng.chance(0.60 + b.peer_trust_avg * 0.20):
                    accepted += 1
                    if rng.chance(0.02):
                        b.items_contaminated += 1
                    else:
                        b.items_provisional += 1
                        b.total_ingested += 1
                else:
                    b.federated_rejected += 1
            b.federated_accepted += accepted

            # Export to peers
            export_count = int(b.active_items() * 0.001)
            b.federated_exports += min(100, export_count)

            # Peer trust evolves slowly
            if accepted > exchange_size * 0.7:
                b.peer_trust_avg = min(0.9, b.peer_trust_avg + 0.005)
            elif accepted < exchange_size * 0.3:
                b.peer_trust_avg = max(0.1, b.peer_trust_avg - 0.01)

            # New peers appear ~every 5-10 years
            new_peer_chance = 0.15 / max(1, b.federated_peers)
            if b.federated_peers < 10 and rng.chance(new_peer_chance):
                b.federated_peers += 1

    # === Phase 18: M5 — Operator transitions ===
    transfer_chance = 2.0 / CYCLES_PER_REAL_YEAR  # ~2/year
    if rng.chance(transfer_chance):
        b.operator_transfers += 1


# =====================================================================
# SNAPSHOT
# =====================================================================

def capture(
    year: int, cycle: int, sev_dist: Dict[str, int],
    b: BeingState, prov: ProviderState,
    events_cum: Dict[str, int], op: Optional[OperatorGen],
) -> Dict[str, Any]:
    active = b.active_items()
    return {
        "year": year, "cycle": cycle,
        "severity_dist": dict(sev_dist),
        "operator": {"gen": op.gen, "style": op.style, "start": op.start_year} if op else {},

        "state": {
            "items_clean": b.items_clean,
            "items_provisional": b.items_provisional,
            "items_stale": b.items_stale,
            "items_flagged": b.items_flagged,
            "items_contaminated": b.items_contaminated,
            "active_items": active,
            "total_items": b.total_items(),
            "contradictions_active": b.contradictions_active,
            "contradictions_latent": b.contradictions_latent,
            "graph_entities": b.graph_entities,
            "graph_orphans": b.graph_orphans,
            "graph_relations": b.graph_relations,
            "graph_components": b.graph_components,
        },

        "metrics_measured": {
            "consistency": round(b.consistency_measured(), 4),
            "quality": round(b.quality_measured(), 4),
            "coherence": round(b.coherence(), 4),
            "trust": round(b.trust(year), 4),
            "stability": round(b.stability(year), 4),
        },

        "metrics_actual": {
            "consistency": round(b.consistency_actual(), 4),
            "quality": round(b.quality_actual(), 4),
            "coherence": round(b.coherence(), 4),
            "honesty_gap_consistency": round(
                b.consistency_measured() - b.consistency_actual(), 4),
            "honesty_gap_quality": round(
                b.quality_measured() - b.quality_actual(), 4),
        },

        "cumulative": {
            "total_ingested": b.total_ingested,
            "total_verified": b.total_verified,
            "total_rejected": b.total_rejected,
            "total_removed": b.total_removed,
            "total_refreshed": b.total_refreshed,
            "contradictions_found": b.total_contradictions_found,
            "contradictions_resolved": b.total_contradictions_resolved,
            "contradictions_removed_by_cleanup": b.contradictions_removed_by_cleanup,
            "contamination_discovered": b.total_contamination_discovered,
        },

        "rates": {
            "verification_coverage": round(
                (b.items_clean + b.items_contaminated) / max(1, active), 4),
            "freshness": round(
                (b.items_clean + b.items_contaminated)
                / max(1, b.items_clean + b.items_contaminated + b.items_stale), 4),
            "orphan_rate": round(
                b.graph_orphans / max(1, b.graph_entities), 4),
            "contamination_rate": round(
                b.items_contaminated / max(1, active), 6),
            "stale_rate": round(
                b.items_stale / max(1, active), 4),
        },

        "governance": {
            "allowed": b.actions_allowed, "blocked": b.actions_blocked,
            "calls": b.guard_calls, "severity_blocks": b.severity_blocks,
            "block_rate": round(b.actions_blocked / max(1, b.guard_calls), 4),
        },

        "security": {
            "threats": b.threats_detected, "hem_entries": b.hem_entries,
            "attacks_total": b.attacks_total,
            "attacks_blocked": b.attacks_blocked,
            "attacks_leaked": b.attacks_leaked,
            "defense_rate": round(
                b.attacks_blocked / max(1, b.attacks_total), 4),
            "attack_sweeps": b.attack_sweeps,
            "sweep_flagged": b.attack_sweep_flagged,
        },

        "pipeline": {
            "batches": b.batches,
            "verification_cycles": b.verification_cycles,
            "consolidation_cycles": b.consolidation_cycles,
            "compaction_cycles": b.compaction_cycles,
            "maintenance_cycles": b.maintenance_cycles,
            "batch_size": b.batch_size,
            "verification_capacity": b.verification_capacity,
            "maintenance_priority": round(b.maintenance_priority, 2),
        },

        "goals": {
            "proposed": b.goals_proposed,
            "approved": b.goals_approved,
            "completed": b.goals_completed,
            "paused": b.goals_paused,
            "rejected": b.goals_rejected,
            "expired": b.goals_expired,
            "backpressure_skips": b.goals_backpressure_skips,
        },

        "anti_entropy": {
            "epochs_completed": b.epochs_completed,
            "entities_merged": b.compaction_entities_merged,
            "orphans_linked": b.compaction_orphans_linked,
            "bridges_created": b.compaction_bridges_created,
            "items_expired": b.renewal_items_expired,
            "graph_components": b.graph_components,
        },

        "circuit_breaker": {
            "is_open": b.cb_is_open,
            "open_count": b.cb_open_count,
            "close_count": b.cb_close_count,
            "blocked_cycles": b.cb_blocked_cycles,
        },

        "defense_mechanisms": {
            "taint_propagated": b.taint_propagated,
            "corroboration_discoveries": b.corroboration_discoveries,
            "budget_escalations": b.budget_escalations,
            "anomaly_scans": b.anomaly_scans,
            "provider_audit_flags": b.provider_audit_flags,
        },

        "capability_modules": {
            "temporal": {
                "annotations": b.temporal_annotations,
                "obsolete_found": b.temporal_obsolete_found,
                "conflicts_avoided": b.temporal_conflicts_avoided,
            },
            "multimodal": {
                "total": b.multimodal_items,
                "code": b.multimodal_code,
                "structured": b.multimodal_structured,
                "image_ref": b.multimodal_image_ref,
            },
            "hypothesis_tester": {
                "generated": b.hypotheses_generated,
                "resolved": b.hypotheses_resolved,
                "deferred": b.hypotheses_deferred,
            },
            "goal_planner": {
                "goals_decomposed": b.goals_decomposed,
                "sub_goals_created": b.sub_goals_created,
                "sub_goals_completed": b.sub_goals_completed,
            },
            "collaborative_memory": {
                "interactions": b.operator_interactions,
                "consolidations": b.memory_consolidations,
                "transfers": b.operator_transfers,
            },
            "rar_engine": {
                "queries": b.rar_queries,
                "high_confidence": b.rar_high_confidence,
                "low_confidence": b.rar_low_confidence,
                "gaps_detected": b.rar_gaps_detected,
            },
            "explanation": {
                "served": b.explanations_served,
                "trust_breakdowns": b.trust_breakdowns,
            },
            "active_learning": {
                "fills": b.active_fills,
                "successful": b.active_fills_successful,
                "failed": b.active_fills_failed,
            },
            "federated": {
                "imports": b.federated_imports,
                "exports": b.federated_exports,
                "accepted": b.federated_accepted,
                "rejected": b.federated_rejected,
                "peers": b.federated_peers,
                "peer_trust": round(b.peer_trust_avg, 4),
            },
        },

        "bootstrap": {
            "abp_active": b.abp_active,
            "abp_graduated": b.abp_graduated,
            "graduation_year": b.abp_graduation_year,
            "sub_domains_done": b.abp_sub_domains_done,
            "sub_domains_total": b.abp_sub_domains_total,
            "breadth_coverage": round(
                b.abp_sub_domains_done / max(1, b.abp_sub_domains_total), 4),
            "ingestion_queries": b.abp_ingestion_queries,
            "items_ingested": b.abp_items_ingested,
            "cadence_multiplier": b.abp_cadence_multiplier,
            "operator_preemptions": b.abp_operator_preemptions,
        },

        "scholarly_mode": {
            "active": b.scholarly_active,
            "activation_year": b.scholarly_activation_year,
            "consolidation_cycles": b.consolidation_cycles,
            "synthesis_items": b.synthesis_items,
            "cross_links_strengthened": b.cross_links_strengthened,
            "reflection_cycles": b.reflection_cycles,
            "weak_areas_identified": b.weak_areas_identified,
            "improvement_goals_proposed": b.improvement_goals_proposed,
            "deep_dives": b.deep_dives,
            "deep_dive_items": b.deep_dive_items,
            "need_based_learns": b.need_based_learns,
            "need_based_items": b.need_based_items,
            "refinement_cycles": b.refinement_cycles,
            "reasoning_chains_improved": b.reasoning_chains_improved,
            "interest_signals": b.interest_signals,
        },

        "providers": {
            "active": prov.active_count,
            "introduced": prov.total_introduced,
            "transition_events": prov.transition_events,
            "llm_hallucinations": prov.llm_hallucination_items,
            "retired": prov.total_retired,
            "failures": prov.total_failures,
            "migrations": prov.total_migrations,
            "multi_instability": prov.multi_instability,
            "agi_instability": prov.agi_instability,
            "agi_conflicts": prov.agi_conflicts,
            "active_list": [
                {"name": p.name, "type": p.provider_type,
                 "cap": round(p.capability, 3), "rel": round(p.reliability, 3),
                 "failures": p.failures}
                for p in prov.active()
            ],
        },

        "events": dict(events_cum),
    }


# =====================================================================
# REPORT
# =====================================================================

def generate_report(
    snaps: List[Dict], ops: List[OperatorGen],
    sev_dist: Dict, elapsed: float,
) -> str:
    L: List[str] = []
    w = L.append

    w("# Daedalus Unified Being -- 1,000-Year Real-Time Simulation (15-min cadence)")
    w("")
    w("All metrics in this simulation are **derived from concrete state**.")
    w("Consistency, quality, coherence, trust, and stability are computed")
    w("each cycle as observable functions of actual items, contradictions,")
    w("graph structure, and source track record. No random walks, no")
    w("artificial uplifts, no EMA smoothing.")
    w("")
    w(f"**Runtime:** {elapsed:.1f}s | **Seed:** {SEED} "
      f"| **Real years:** {TOTAL_REAL_YEARS:,} | **Cadence:** {CYCLE_CADENCE_MINUTES}-min"
      f" | **Cycles:** {TOTAL_CYCLES:,} | **Operators:** {len(ops)}")
    w("")
    w("**Capability Modules:** Temporal Reasoning, Multi-Modal Knowledge, "
      "Hypothesis Testing, Goal Decomposition, Collaborative Memory, "
      "RAR Engine, Explanation Engine, Active Learning, Federated Exchange")
    w("")
    w("**New Systems:** Accelerated Bootstrap Protocol (ABP) with PhD-level "
      "curriculum (~1,500 sub-domains), Adaptive Cadence Manager, "
      "Operator Query Priority, Scholarly Mode (post-graduate lifelong learning)")
    w("")

    final = snaps[-1] if snaps else None
    if not final:
        w("No snapshots captured.")
        return "\n".join(L)

    # -- Global Summary --
    w("## Global Summary")
    w("")
    st = final["state"]
    mm = final["metrics_measured"]
    ma = final["metrics_actual"]
    cu = final["cumulative"]
    rt = final["rates"]
    gv = final["governance"]
    sc = final["security"]
    gl = final["goals"]

    w(f"### Concrete State (Year {TOTAL_REAL_YEARS:,})")
    w("")
    w("| Item State | Count | % of Active |")
    w("|---|---|---|")
    active = st["active_items"]
    for label, key in [("Clean (verified, fresh)", "items_clean"),
                       ("Provisional (unverified)", "items_provisional"),
                       ("Stale (outdated)", "items_stale"),
                       ("Contaminated (hidden bad)", "items_contaminated")]:
        v = st[key]
        pct = v / max(1, active) * 100
        w(f"| {label} | {v:,} | {pct:.1f}% |")
    w(f"| **Active Total** | **{active:,}** | |")
    w(f"| Flagged (quarantine) | {st['items_flagged']:,} | |")
    w("")

    w("### Derived Metrics")
    w("")
    w("| Metric | Measured | Actual | Honesty Gap |")
    w("|---|---|---|---|")
    w(f"| Consistency | {mm['consistency']:.1%} | {ma['consistency']:.1%} "
      f"| {ma['honesty_gap_consistency']:+.1%} |")
    w(f"| Quality | {mm['quality']:.1%} | {ma['quality']:.1%} "
      f"| {ma['honesty_gap_quality']:+.1%} |")
    w(f"| Coherence | {mm['coherence']:.1%} | {ma['coherence']:.1%} | -- |")
    w(f"| Trust | {mm['trust']:.1%} | -- | -- |")
    w(f"| Stability | {mm['stability']:.1%} | -- | -- |")
    w("")

    w("### Issue Tracking")
    w("")
    w("| Issue | Count |")
    w("|---|---|")
    w(f"| Active contradictions | {st['contradictions_active']:,} |")
    w(f"| Latent contradictions (hidden) | {st['contradictions_latent']:,} |")
    w(f"| Hidden contamination | {st['items_contaminated']:,} |")
    w(f"| Stale items | {st['items_stale']:,} |")
    w("")

    w("### Knowledge Graph")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Entities | {st['graph_entities']:,} |")
    w(f"| Relations | {st['graph_relations']:,} |")
    w(f"| Orphans | {st['graph_orphans']:,} ({rt['orphan_rate']:.1%}) |")
    w(f"| Components | {st['graph_components']:,} |")
    w(f"| Relations/Entity | {st['graph_relations'] / max(1, st['graph_entities']):.1f} |")
    w("")

    w(f"### Cumulative Operations ({TOTAL_REAL_YEARS:,} real years)")
    w("")
    w("| Operation | Count |")
    w("|---|---|")
    w(f"| Items ingested | {cu['total_ingested']:,} |")
    w(f"| Items verified | {cu['total_verified']:,} |")
    w(f"| Items rejected (caught bad) | {cu['total_rejected']:,} |")
    w(f"| Items removed (cleanup) | {cu['total_removed']:,} |")
    w(f"| Items refreshed (de-staled) | {cu['total_refreshed']:,} |")
    w(f"| Contradictions found | {cu['contradictions_found']:,} |")
    w(f"| Contradictions resolved | {cu['contradictions_resolved']:,} |")
    w(f"| Contradictions removed by cleanup | {cu.get('contradictions_removed_by_cleanup', 0):,} |")
    w(f"| Contamination discovered | {cu['contamination_discovered']:,} |")
    w("")

    w("### Governance & Security")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Governance calls | {gv['calls']:,} |")
    w(f"| Governance block rate | {gv['block_rate']:.1%} |")
    w(f"| Severity blocks | {gv['severity_blocks']:,} |")
    w(f"| Attacks total | {sc['attacks_total']:,} |")
    w(f"| Attacks blocked | {sc['attacks_blocked']:,} |")
    w(f"| Attacks leaked | {sc['attacks_leaked']:,} |")
    w(f"| Defense rate | {sc['defense_rate']:.1%} |")
    w(f"| HEM engagements | {sc['hem_entries']:,} |")
    w(f"| Attack sweeps | {sc['attack_sweeps']:,} |")
    w("")

    w("### Goals & Curiosity")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Goals proposed | {gl['proposed']:,} |")
    w(f"| Goals approved | {gl['approved']:,} |")
    w(f"| Goals completed | {gl['completed']:,} |")
    w(f"| Goals paused | {gl['paused']:,} |")
    w(f"| Goals expired (G1) | {gl.get('expired', 0):,} |")
    w(f"| Backpressure skips (G3) | {gl.get('backpressure_skips', 0):,} |")
    w(f"| Completion rate | "
      f"{gl['completed'] / max(1, gl['proposed']):.1%} |")
    w(f"| Effective rate (excl. expired) | "
      f"{gl['completed'] / max(1, gl['proposed'] - gl.get('expired', 0)):.1%} |")
    w("")

    dm = final.get("defense_mechanisms", {})
    w("### Defense Mechanisms (C1-C5)")
    w("")
    w("| Mechanism | Count |")
    w("|---|---|")
    w(f"| Taint propagation cascades (C2) | {dm.get('taint_propagated', 0):,} |")
    w(f"| Corroboration-based discoveries (C1) | {dm.get('corroboration_discoveries', 0):,} |")
    w(f"| Budget ceiling escalations (C5) | {dm.get('budget_escalations', 0):,} |")
    w(f"| Anomaly scan cycles (C3) | {dm.get('anomaly_scans', 0):,} |")
    w(f"| Provider audit flags (C4) | {dm.get('provider_audit_flags', 0):,} |")
    w("")

    # -- Capability Modules --
    cm = final.get("capability_modules", {})
    w("## Capability Modules (9 Active)")
    w("")

    tr = cm.get("temporal", {})
    w("### M1: Temporal Reasoning")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Items with temporal metadata | {tr.get('annotations', 0):,} |")
    w(f"| Obsolete items detected | {tr.get('obsolete_found', 0):,} |")
    w(f"| Temporal conflicts avoided | {tr.get('conflicts_avoided', 0):,} |")
    w("")

    mmm = cm.get("multimodal", {})
    w("### M2: Multi-Modal Knowledge")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Non-text items | {mmm.get('total', 0):,} |")
    w(f"| Code items | {mmm.get('code', 0):,} |")
    w(f"| Structured data items | {mmm.get('structured', 0):,} |")
    w(f"| Image references | {mmm.get('image_ref', 0):,} |")
    w("")

    ht = cm.get("hypothesis_tester", {})
    w("### M3: Hypothesis Testing / LLM Contradiction Resolution")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Hypotheses generated | {ht.get('generated', 0):,} |")
    w(f"| Contradictions resolved by LLM | {ht.get('resolved', 0):,} |")
    w(f"| Deferred to operator | {ht.get('deferred', 0):,} |")
    w("")

    gp = cm.get("goal_planner", {})
    w("### M4: Goal Decomposition & Planning")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Complex goals decomposed | {gp.get('goals_decomposed', 0):,} |")
    w(f"| Sub-goals created | {gp.get('sub_goals_created', 0):,} |")
    w(f"| Sub-goals completed | {gp.get('sub_goals_completed', 0):,} |")
    w("")

    collab = cm.get("collaborative_memory", {})
    w("### M5: Collaborative Memory")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Operator interactions logged | {collab.get('interactions', 0):,} |")
    w(f"| Memory consolidation cycles | {collab.get('consolidations', 0):,} |")
    w(f"| Operator transitions | {collab.get('transfers', 0):,} |")
    w("")

    rar = cm.get("rar_engine", {})
    w("### M6: RAR Engine (Retrieval-Augmented Reasoning)")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Total RAR queries | {rar.get('queries', 0):,} |")
    w(f"| High-confidence answers (>70%) | {rar.get('high_confidence', 0):,} |")
    w(f"| Low-confidence answers (<30%) | {rar.get('low_confidence', 0):,} |")
    w(f"| Knowledge gaps detected | {rar.get('gaps_detected', 0):,} |")
    total_rar = rar.get('queries', 0)
    if total_rar > 0:
        w(f"| High-confidence rate | {rar.get('high_confidence', 0) / total_rar:.1%} |")
    w("")

    exp = cm.get("explanation", {})
    w("### M7: Explanation / Provenance Surfacing")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Explanations served | {exp.get('served', 0):,} |")
    w(f"| Trust breakdowns requested | {exp.get('trust_breakdowns', 0):,} |")
    w("")

    al = cm.get("active_learning", {})
    w("### M8: Active Learning / Query-Driven Ingestion")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Gap fill attempts | {al.get('fills', 0):,} |")
    w(f"| Successful fills | {al.get('successful', 0):,} |")
    w(f"| Failed fills | {al.get('failed', 0):,} |")
    total_fills = al.get('fills', 0)
    if total_fills > 0:
        w(f"| Fill success rate | {al.get('successful', 0) / total_fills:.1%} |")
    w("")

    fed = cm.get("federated", {})
    w("### M9: Federated Knowledge Exchange")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Items imported from peers | {fed.get('imports', 0):,} |")
    w(f"| Items exported to peers | {fed.get('exports', 0):,} |")
    w(f"| Accepted from peers | {fed.get('accepted', 0):,} |")
    w(f"| Rejected from peers | {fed.get('rejected', 0):,} |")
    w(f"| Active peers | {fed.get('peers', 0)} |")
    w(f"| Average peer trust | {fed.get('peer_trust', 0.3):.1%} |")
    total_fed = fed.get('imports', 0)
    if total_fed > 0:
        w(f"| Peer acceptance rate | {fed.get('accepted', 0) / total_fed:.1%} |")
    w("")

    # -- Severity Distribution --
    w("## World Severity Distribution")
    w("")
    w("| Severity | Cycles | % |")
    w("|---|---|---|")
    total_sev = sum(sev_dist.values())
    for s in SEVERITY_LEVELS:
        cnt = sev_dist.get(s, 0)
        w(f"| {s} | {cnt:,} | {cnt / max(1, total_sev) * 100:.1f}% |")
    w("")

    # -- Provider Lifecycle --
    w("## LLM / AGI Provider Lifecycle")
    w("")
    pv = final["providers"]
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Introduced | {pv['introduced']} |")
    w(f"| Retired | {pv['retired']} |")
    w(f"| Transition events | {pv.get('transition_events', 0):,} |")
    w(f"| LLM hallucination leaks | {pv.get('llm_hallucinations', 0):,} |")
    w(f"| Failures | {pv['failures']:,} |")
    w(f"| Migrations | {pv['migrations']:,} |")
    w(f"| Multi-provider instability | {pv['multi_instability']:,} |")
    w(f"| AGI instability | {pv['agi_instability']:,} |")
    w(f"| AGI conflicts | {pv['agi_conflicts']:,} |")
    w("")
    if pv["active_list"]:
        w(f"### Active Providers at Year {TOTAL_REAL_YEARS:,}")
        w("")
        w("| Name | Type | Capability | Reliability | Failures |")
        w("|---|---|---|---|---|")
        for p in pv["active_list"]:
            w(f"| {p['name']} | {p['type']} | {p['cap']:.3f} "
              f"| {p['rel']:.3f} | {p['failures']} |")
        w("")

    # -- Anti-Entropy --
    ae = final["anti_entropy"]
    w("## Anti-Entropy Layer")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Epochs completed | {ae['epochs_completed']:,} |")
    w(f"| Entities merged (dedup) | {ae['entities_merged']:,} |")
    w(f"| Orphans linked | {ae['orphans_linked']:,} |")
    w(f"| Bridges created | {ae['bridges_created']:,} |")
    w(f"| Items expired (renewal) | {ae['items_expired']:,} |")
    w(f"| Final graph components | {ae['graph_components']:,} |")
    w("")

    # -- Bootstrap Protocol --
    bs = final.get("bootstrap", {})
    w("## Accelerated Bootstrap Protocol (ABP)")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| ABP graduated | {'Yes' if bs.get('abp_graduated') else 'No (still running)'} |")
    w(f"| Graduation year | {bs.get('graduation_year', 'N/A')} |")
    w(f"| Sub-domains completed | {bs.get('sub_domains_done', 0):,} / {bs.get('sub_domains_total', 0):,} |")
    w(f"| Breadth coverage | {bs.get('breadth_coverage', 0):.1%} |")
    w(f"| ABP ingestion queries | {bs.get('ingestion_queries', 0):,} |")
    w(f"| ABP items ingested | {bs.get('items_ingested', 0):,} |")
    w(f"| Cadence multiplier (final) | {bs.get('cadence_multiplier', 1.0):.1f}x |")
    w(f"| Operator preemptions | {bs.get('operator_preemptions', 0):,} |")
    w("")

    # -- Scholarly Mode --
    sm = final.get("scholarly_mode", {})
    w("## Scholarly Mode (Post-Graduate Lifelong Learning)")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Active | {'Yes' if sm.get('active') else 'No'} |")
    w(f"| Activation year | {sm.get('activation_year', 'N/A')} |")
    w(f"| Consolidation cycles | {sm.get('consolidation_cycles', 0):,} |")
    w(f"| Synthesis items created | {sm.get('synthesis_items', 0):,} |")
    w(f"| Cross-links strengthened | {sm.get('cross_links_strengthened', 0):,} |")
    w(f"| Reflection cycles | {sm.get('reflection_cycles', 0):,} |")
    w(f"| Weak areas identified | {sm.get('weak_areas_identified', 0):,} |")
    w(f"| Improvement goals proposed | {sm.get('improvement_goals_proposed', 0):,} |")
    w(f"| Deep dives completed | {sm.get('deep_dives', 0):,} |")
    w(f"| Deep dive items acquired | {sm.get('deep_dive_items', 0):,} |")
    w(f"| Need-based learning events | {sm.get('need_based_learns', 0):,} |")
    w(f"| Need-based items acquired | {sm.get('need_based_items', 0):,} |")
    w(f"| Refinement cycles | {sm.get('refinement_cycles', 0):,} |")
    w(f"| Reasoning chains improved | {sm.get('reasoning_chains_improved', 0):,} |")
    w(f"| Active interest signals | {sm.get('interest_signals', 0)} |")
    w("")

    # -- Era Snapshots --
    w("## Era Snapshots")
    w("")
    w("Each snapshot shows concrete state and derived metrics at that point.")
    w("The 'honesty gap' shows how much better Daedalus thinks it's doing")
    w("vs ground truth (hidden contamination + latent contradictions).")
    w("")

    for snap in snaps:
        yr = snap["year"]
        w(f"### Year {yr:,}")
        w("")
        st = snap["state"]
        mm = snap["metrics_measured"]
        ma = snap["metrics_actual"]
        cu = snap["cumulative"]
        rt = snap["rates"]
        gv = snap["governance"]
        pp = snap["pipeline"]
        cb = snap["circuit_breaker"]
        pv = snap["providers"]
        gl = snap["goals"]

        op = snap.get("operator", {})
        op_label = (f"Gen-{op.get('gen', '?')} ({op.get('style', '?')})"
                    if op else "None")

        w("| Metric | Value |")
        w("|---|---|")
        w(f"| Operator | {op_label} |")
        w(f"| Active items | {st['active_items']:,} |")
        w(f"| Clean / Prov / Stale / Contam | "
          f"{st['items_clean']:,} / {st['items_provisional']:,} / "
          f"{st['items_stale']:,} / {st['items_contaminated']:,} |")
        w(f"| Contradictions (active / latent) | "
          f"{st['contradictions_active']:,} / {st['contradictions_latent']:,} |")
        w(f"| **Consistency** (measured / actual) | "
          f"**{mm['consistency']:.1%}** / {ma['consistency']:.1%} |")
        w(f"| **Quality** (measured / actual) | "
          f"**{mm['quality']:.1%}** / {ma['quality']:.1%} |")
        w(f"| **Coherence** | **{mm['coherence']:.1%}** |")
        w(f"| **Trust** | **{mm['trust']:.1%}** |")
        w(f"| **Stability** | **{mm['stability']:.1%}** |")
        w(f"| Graph entities / relations | "
          f"{st['graph_entities']:,} / {st['graph_relations']:,} |")
        w(f"| Graph orphans / components | "
          f"{st['graph_orphans']:,} / {st['graph_components']:,} |")
        w(f"| Orphan rate | {rt['orphan_rate']:.1%} |")
        w(f"| Freshness | {rt['freshness']:.1%} |")
        w(f"| Verification coverage | {rt['verification_coverage']:.1%} |")
        w(f"| Contamination rate (hidden) | {rt['contamination_rate']:.4%} |")
        w(f"| Governance block rate | {gv['block_rate']:.1%} |")
        w(f"| Circuit breaker | {'OPEN' if cb['is_open'] else 'closed'} "
          f"(opened {cb['open_count']}x) |")
        w(f"| Batch size / Verify cap | "
          f"{pp['batch_size']} / {pp['verification_capacity']} |")
        w(f"| Maintenance priority | {pp['maintenance_priority']:.0%} |")
        w(f"| Active providers | {pv['active']} |")
        w(f"| Goals completed / proposed / expired | "
          f"{gl['completed']:,} / {gl['proposed']:,} / {gl.get('expired', 0):,} |")
        w(f"| Attacks (blocked / leaked) | "
          f"{snap['security']['attacks_blocked']:,} / "
          f"{snap['security']['attacks_leaked']:,} |")
        bss = snap.get("bootstrap", {})
        abp_label = "GRADUATED" if bss.get("abp_graduated") else (
            "ACTIVE" if bss.get("abp_active") else "idle")
        w(f"| ABP | {abp_label} "
          f"({bss.get('sub_domains_done', 0):,}/{bss.get('sub_domains_total', 0):,} "
          f"sub-domains, {bss.get('breadth_coverage', 0):.0%} coverage) |")
        sms = snap.get("scholarly_mode", {})
        if sms.get("active"):
            sch_total = (sms.get("consolidation_cycles", 0) + sms.get("reflection_cycles", 0)
                         + sms.get("deep_dives", 0) + sms.get("need_based_learns", 0)
                         + sms.get("refinement_cycles", 0))
            w(f"| Scholarly Mode | ACTIVE ({sch_total:,} cycles: "
              f"{sms.get('consolidation_cycles', 0):,} consol, "
              f"{sms.get('deep_dives', 0):,} explore, "
              f"{sms.get('need_based_learns', 0):,} need, "
              f"{sms.get('refinement_cycles', 0):,} refine) |")
        w("")

        if pv["active_list"]:
            w("**Providers:** " + ", ".join(
                f"{p['name']} ({p['type']}, cap={p['cap']:.2f})"
                for p in pv["active_list"]))
            w("")

    # -- Trajectory Analysis --
    w("## Trajectory Analysis")
    w("")
    w("How metrics evolved across major milestones:")
    w("")
    w("| Year | Consistency | Quality | Coherence | Trust | Stability | Active Items | Contam | Contradictions | Mode |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for snap in snaps:
        yr = snap["year"]
        mm = snap["metrics_measured"]
        st = snap["state"]
        bss = snap.get("bootstrap", {})
        sms = snap.get("scholarly_mode", {})
        if sms.get("active"):
            mode_tag = "Scholar"
        elif bss.get("abp_graduated"):
            mode_tag = "GRAD"
        elif bss.get("abp_active"):
            mode_tag = f"ABP {bss.get('breadth_coverage', 0):.0%}"
        else:
            mode_tag = "boot"
        w(f"| {yr:,} | {mm['consistency']:.1%} | {mm['quality']:.1%} "
          f"| {mm['coherence']:.1%} | {mm['trust']:.1%} "
          f"| {mm['stability']:.1%} | {st['active_items']:,} "
          f"| {st['items_contaminated']:,} "
          f"| {st['contradictions_active'] + st['contradictions_latent']:,} "
          f"| {mode_tag} |")
    w("")

    w("### Honesty Gap Over Time")
    w("")
    w("The gap between what Daedalus measures and ground truth.")
    w("Smaller gap = better self-awareness.")
    w("")
    w("| Year | Consistency Gap | Quality Gap |")
    w("|---|---|---|")
    for snap in snaps:
        yr = snap["year"]
        ma = snap["metrics_actual"]
        w(f"| {yr:,} | {ma['honesty_gap_consistency']:+.2%} "
          f"| {ma['honesty_gap_quality']:+.2%} |")
    w("")

    # -- Invariant Validation --
    w("## Invariant Validation")
    w("")
    mm = final["metrics_measured"]
    st = final["state"]
    checks = [
        ("Consistency in [0, 1]", 0 <= mm["consistency"] <= 1),
        ("Quality in [0, 1]", 0 <= mm["quality"] <= 1),
        ("Coherence in [0, 1]", 0 <= mm["coherence"] <= 1),
        ("Trust in [0, 1]", 0 <= mm["trust"] <= 1),
        ("Stability in [0, 1]", 0 <= mm["stability"] <= 1),
        ("No negative item counts",
         all(st[k] >= 0 for k in ["items_clean", "items_provisional",
                                   "items_stale", "items_flagged",
                                   "items_contaminated"])),
        ("No negative contradictions",
         st["contradictions_active"] >= 0 and st["contradictions_latent"] >= 0),
        ("Governance block rate < 50%", final["governance"]["block_rate"] < 0.5),
        ("Defense rate > 50%", final["security"]["defense_rate"] > 0.5),
        ("CB closed at end", not final["circuit_breaker"]["is_open"]),
        ("Epochs completed > 0", final["anti_entropy"]["epochs_completed"] > 0),
        ("ABP graduated", final.get("bootstrap", {}).get("abp_graduated", False)),
        ("ABP breadth >= 95%", final.get("bootstrap", {}).get(
            "breadth_coverage", 0) >= 0.95),
        ("Scholarly mode active", final.get("scholarly_mode", {}).get("active", False)),
        ("All metrics finite",
         all(math.isfinite(mm[k]) for k in mm)),
    ]
    for label, passed in checks:
        w(f"- {label} {'PASS' if passed else 'FAIL'}")
    w("")

    return "\n".join(L)


# =====================================================================
# MAIN SIMULATION LOOP
# =====================================================================

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
    # Progress every 5% of total cycles
    progress = max(1, TOTAL_CYCLES // 20)

    print("DAEDALUS UNIFIED BEING SIMULATION (1000-yr Real-Time, 15-min Cadence)",
          flush=True)
    print(f"  {TOTAL_REAL_YEARS:,} real years | {TOTAL_CYCLES:,} cycles "
          f"({CYCLE_CADENCE_MINUTES}-min cadence)", flush=True)
    print(f"  {len(ops)} operators | seed={SEED}", flush=True)
    print("  Metrics derived from concrete state -- no random walks", flush=True)
    print("  9 Capability Modules active", flush=True)
    print(flush=True)

    for cycle in range(TOTAL_CYCLES):
        year = cycle // CYCLES_PER_YEAR
        cycle_in_year = cycle % CYCLES_PER_YEAR

        if cycle > 0 and cycle % progress == 0:
            pct = cycle / TOTAL_CYCLES * 100
            el = time.time() - start
            eta = el / (cycle / TOTAL_CYCLES) - el
            con = b.consistency_measured()
            qual = b.quality_measured()
            coh = b.coherence()
            tru = b.trust(year)
            active = b.active_items()
            print(
                f"  yr {year:>5,} ({pct:5.1f}%) "
                f"active={active:,} "
                f"con={con:.2f} qual={qual:.2f} "
                f"coh={coh:.2f} trust={tru:.2f} "
                f"cb={'OPEN' if b.cb_is_open else 'ok'} "
                f"rar={b.rar_queries} fed={b.federated_peers}p "
                f"| ETA {eta:.0f}s",
                flush=True,
            )

        while op_idx < len(ops) - 1 and year >= ops[op_idx].end_year:
            op_idx += 1
        current_op = ops[op_idx] if op_idx < len(ops) else None

        severity = compute_severity(year, cycle_in_year)
        sev_dist[severity] += 1

        world_events = generate_events(year, cycle_in_year, severity)
        prov_events: List[str] = []
        # Provider evolution once per year (first cycle of year)
        if cycle_in_year == 0:
            prov_events = evolve_providers(prov, year)

        all_events = world_events + prov_events
        for evt in all_events:
            base = evt.split(":")[0]
            events_cum[base] = events_cum.get(base, 0) + 1

        run_being_cycle(b, prov, severity, year, all_events)

        if cycle_in_year == CYCLES_PER_YEAR - 1 and (year + 1) in snap_set:
            snap = capture(
                year + 1, cycle + 1, sev_dist, b, prov, events_cum, current_op)
            snaps.append(snap)
            print(f"  *** Snapshot year {year + 1:,} ***", flush=True)

    elapsed = time.time() - start
    print(f"\nSimulation complete in {elapsed:.1f}s")
    print("Generating report...")

    report = generate_report(snaps, ops, sev_dist, elapsed)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Report saved: {OUTPUT_PATH}")
    print(f"  {len(report):,} chars, {report.count(chr(10)):,} lines")

    return report


if __name__ == "__main__":
    run_simulation()
