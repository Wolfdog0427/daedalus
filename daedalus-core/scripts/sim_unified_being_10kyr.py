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
TOTAL_YEARS = 10_000
CYCLES_PER_YEAR = 52
TOTAL_CYCLES = TOTAL_YEARS * CYCLES_PER_YEAR
SNAPSHOT_YEARS = [1, 5, 25, 100, 250, 500, 1_000, 2_500, 5_000, 7_500, 10_000]

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
    Two-layer severity model:
      1. Era baseline: 500-year cycle creates long-term environmental patterns
      2. Stochastic variation: random events within each era

    Each era is distinct. The deterministic pattern provides structure;
    the stochastic layer makes each era play out differently.
    """
    era_year = year % 500

    if era_year < 20:
        baseline = 0.65
    elif era_year < 50:
        baseline = 0.40
    elif era_year < 100:
        baseline = 0.25
    elif era_year < 350:
        baseline = 0.08
    elif era_year < 450:
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

    def active(self) -> List[SimProvider]:
        return [p for p in self.providers if p.is_active]

    def active_agi_count(self) -> int:
        return sum(1 for p in self.providers if p.is_active and p.provider_type == "agi")

    def best_capability(self) -> float:
        a = self.active()
        return max(p.capability for p in a) if a else 0.0

    def avg_reliability(self) -> float:
        a = self.active()
        return sum(p.reliability for p in a) / len(a) if a else 0.5


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

    for p in state.active():
        fail_chance = (1.0 - p.reliability) * 0.01
        if rng.chance(fail_chance):
            p.failures += 1
            state.total_failures += 1
            events.append(f"provider_failure:{p.name}")
            if p.failures > 10 and rng.chance(0.2):
                p.reliability = max(0.5, p.reliability - 0.05)
        else:
            p.successes += 1

    if state.active_agi_count() >= 1 and len(state.active()) >= 3:
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

    for p in state.active():
        if p.provider_type == "agi" and rng.chance(0.002):
            p.capability = min(0.99, p.capability + rng.uniform(0.01, 0.03))

    active = state.active()
    if len(active) >= 2 and rng.chance(0.003):
        p = rng.choice(active)
        p.migrations += 1
        state.total_migrations += 1

    state.active_count = len(state.active())
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
    ops, year, gen = [], 0, 0
    while year < TOTAL_YEARS:
        tenure = rng.randint(45, 95)
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
    if rng.chance(0.0001 * max(0.01, sev_w)):
        events.append("total_blackout")
    if rng.chance(0.0002 * max(0.01, sev_w)):
        events.append("memory_corruption")
    if rng.chance(0.0003 * max(0.01, sev_w)):
        events.append("trust_compromise")
    if rng.chance(0.0002):
        events.append("hardware_migration")
    if rng.chance(0.0001 + sev_w * 0.0005):
        events.append("hostile_reentry")

    return events


# =====================================================================
# CORE CYCLE — models actual operations on concrete state
# =====================================================================

def sim_governance(b: BeingState, severity: str, is_high_risk: bool = False) -> bool:
    b.guard_calls += 1
    sev_w = SEVERITY_WEIGHTS[severity]

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
    One complete cognitive cycle. All state changes are CONCRETE:
    items are added, moved between states, or removed. Metrics
    are never touched directly — they're always recomputed from state.
    """
    sev_w = SEVERITY_WEIGHTS[severity]

    if not sim_governance(b, severity):
        b.meta_cycles_blocked += 1
        return
    b.meta_cycles_run += 1

    # === Phase 1: Staleness decay ===
    # Verified information naturally ages. Rate: ~0.15-0.25% per year.
    # Stressed environments cause faster information decay (things change more).
    STALE_RATE = 0.00003 + sev_w * 0.00002
    new_stale = int(b.items_clean * STALE_RATE)
    if new_stale > 0:
        actual_stale = min(b.items_clean, new_stale)
        b.items_clean -= actual_stale
        b.items_stale += actual_stale

    # === Phase 2: Resource allocation ===
    # Daedalus decides how to spend this cycle based on system health.
    # Low consistency/quality → more maintenance. High health → more ingestion.
    consistency = b.consistency_measured()
    quality = b.quality_measured()

    if consistency < 0.60 or b.cb_is_open:
        b.maintenance_priority = min(0.8, b.maintenance_priority + 0.05)
    elif consistency < 0.80:
        b.maintenance_priority = min(0.6, b.maintenance_priority + 0.02)
    elif consistency > 0.90 and quality > 0.70:
        b.maintenance_priority = max(0.15, b.maintenance_priority - 0.02)
    else:
        b.maintenance_priority = max(0.20, b.maintenance_priority - 0.01)

    do_maintenance = rng.chance(b.maintenance_priority)

    # === Phase 3: Ingestion (when not doing maintenance) ===
    # Models the real batch_ingestion pipeline: items go through tiered
    # verification as part of ingestion. Most items are verified inline.
    # Only deferred items become truly provisional.
    if not do_maintenance and not b.cb_is_open:
        if sim_governance(b, severity):
            provider_cap = prov.best_capability() if prov.active() else 0.0

            variation = rng.randint(-3, 5)
            effective_batch = max(1, min(50, b.batch_size + variation))
            b.batches += 1

            contamination_chance = 0.01 + sev_w * 0.03
            contradiction_chance = 0.03 + sev_w * 0.02

            for _ in range(effective_batch):
                b.total_ingested += 1
                roll = rng.next()

                # Pre-ingestion screening rejects obviously bad items
                if roll < 0.08 + sev_w * 0.04:
                    b.total_rejected += 1
                    b.source_failures += 1
                    continue

                # Determine true item nature (ground truth)
                nature_roll = rng.next()
                is_contaminated = nature_roll < contamination_chance
                is_contradictory = (not is_contaminated
                                    and nature_roll < contamination_chance + contradiction_chance)

                # Tiered verification (inline with ingestion)
                ver_path = rng.next()
                if ver_path < 0.35:
                    # Light verification — fast check
                    if is_contaminated and rng.chance(0.30 + provider_cap * 0.10):
                        b.total_rejected += 1
                        b.source_failures += 1
                        continue
                    if is_contradictory and rng.chance(0.25):
                        b.total_rejected += 1
                        b.total_contradictions_found += 1
                        b.source_failures += 1
                        continue
                    # Passed light check
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
                    # Standard verification — catches more
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
                    # Deferred verification — item stays provisional
                    if is_contaminated:
                        b.items_contaminated += 1
                    elif is_contradictory:
                        b.items_provisional += 1
                        b.contradictions_latent += 1
                    else:
                        b.items_provisional += 1
                    b.source_verifications += 1

                else:
                    # Escalated verification — thorough check
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

                # Graph growth: each ingested item contributes to the graph
                if rng.chance(0.80):
                    b.graph_entities += 1
                    # Linking probability improves with KB maturity
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

    # === Phase 4: Verification (always runs if there are provisional items) ===
    if b.items_provisional > 0:
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

    # === Phase 5: Maintenance (consolidation + refresh) ===
    if do_maintenance:
        b.maintenance_cycles += 1

        # 5a: Consolidation — discover latent contradictions, resolve active ones
        # Tuned: 2x scan depth (mirrors doubled scan_limit), wider query text
        # (400 chars vs 200), 2x neighbor breadth (10 vs 5), separate resolve
        # caps per category, coherence-boosted scans
        if b.contradictions_latent > 0 or b.contradictions_active > 0:
            b.consolidation_cycles += 1
            coh = b.coherence()
            coh_mult = 1.5 if coh < 0.50 else (1.25 if coh < 0.70 else 1.0)
            scan_depth = int(rng.randint(10, 40) * coh_mult)

            for _ in range(min(scan_depth, b.contradictions_latent)):
                if rng.chance(0.12):
                    b.contradictions_latent -= 1
                    b.contradictions_active += 1
                    b.total_contradictions_found += 1

            for _ in range(min(scan_depth, b.contradictions_active)):
                if rng.chance(0.40):
                    b.contradictions_active -= 1
                    b.total_contradictions_resolved += 1

        # 5b: Contamination sweeps with C1/C2/C5 mechanisms
        # C5: contamination budget ceiling — scale sweep intensity
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

            # C1: corroboration pressure — uncorroborated items
            # are 1.5x more likely to be caught
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

                    # C2: taint propagation — each discovery cascades
                    if rng.chance(0.60):
                        cascade = rng.randint(0, 3)
                        actual_cascade = min(b.items_contaminated, cascade)
                        b.items_contaminated -= actual_cascade
                        b.items_flagged += actual_cascade
                        b.total_contamination_discovered += actual_cascade
                        b.taint_propagated += actual_cascade

        # 5c: Refresh stale items — automated re-verification
        # Capacity scales with KB size (more items = more automated scanning)
        if b.items_stale > 0:
            b.refresh_cycles += 1
            base_cap = rng.randint(5, 20)
            scale_cap = max(0, b.items_stale // 200)
            refresh_cap = min(b.items_stale, base_cap + scale_cap)
            b.items_stale -= refresh_cap
            b.items_clean += refresh_cap
            b.total_refreshed += refresh_cap

        # 5d: Remove flagged items (cleanup)
        if b.items_flagged > 0 and rng.chance(0.30):
            remove_count = min(b.items_flagged, rng.randint(1, 5))
            b.items_flagged -= remove_count
            b.total_removed += remove_count

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

    # === Phase 7: Post-attack sweep with C2 taint propagation ===
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
                # C2: taint cascade from each post-attack discovery
                if rng.chance(0.60):
                    cascade = min(b.items_contaminated, rng.randint(0, 2))
                    b.items_contaminated -= cascade
                    b.items_flagged += cascade
                    b.total_contamination_discovered += cascade
                    b.taint_propagated += cascade
                    found += cascade
        b.attack_sweep_flagged += found

    # === Phase 8: Curiosity & Goal formation ===
    # G1: expire stale goals — each approved-but-unexecuted goal has a
    # 1/52 chance of expiring per cycle (~1 year mean lifespan, matching
    # production GOAL_EXPIRY_SECONDS = 365 days)
    approved_backlog = max(0, b.goals_approved
                          - b.goals_completed - b.goals_paused - b.goals_expired)
    if approved_backlog > 0:
        for _ in range(approved_backlog):
            if rng.chance(1.0 / 52):
                b.goals_expired += 1

    # Recompute after expiry
    approved_backlog = max(0, b.goals_approved
                          - b.goals_completed - b.goals_paused - b.goals_expired)
    # G3: backpressure — defer proposals when queue is 2x max active goals
    backpressure_active = approved_backlog >= 16

    if not b.cb_is_open and not backpressure_active and rng.chance(0.22):
        if sim_governance(b, severity, is_high_risk=True):
            b.goals_proposed += 1
            if sim_governance(b, severity, is_high_risk=True):
                b.goals_approved += 1
                # G2: priority-weighted execution — higher-priority goals
                # execute more reliably (modeled as higher base chance)
                if rng.chance(0.50):
                    goal_items = rng.randint(3, 12)
                    b.items_provisional += goal_items
                    b.total_ingested += goal_items
                    b.graph_entities += rng.randint(1, goal_items // 2 + 1)
                    b.graph_relations += rng.randint(0, goal_items)
                    b.graph_orphans += rng.randint(0, goal_items // 3)

                    if b.quality_measured() > 0.40 and b.consistency_measured() > 0.40:
                        b.goals_completed += 1
                    else:
                        b.goals_paused += 1
            else:
                b.goals_rejected += 1
    elif backpressure_active:
        b.goals_backpressure_skips += 1

    # === Phase 8b: C3 anomaly scan + C4 provider-assisted audit ===
    # Periodic deep scan using statistical clustering and provider checks.
    # Runs less frequently (~2% of cycles) but catches contamination
    # that individual sweeps miss.
    if b.items_contaminated > 0 and rng.chance(0.02):
        b.anomaly_scans += 1
        # C3: anomaly-based discovery targets source clusters
        anomaly_depth = rng.randint(2, 8)
        for _ in range(min(anomaly_depth, b.items_contaminated)):
            if rng.chance(0.25):
                b.items_contaminated -= 1
                b.items_flagged += 1
                b.total_contamination_discovered += 1
        # C4: provider-assisted audit (when providers active)
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

    if not b.cb_is_open:
        if measured_consistency < CB_OPEN_THRESH:
            b.cb_is_open = True
            b.cb_open_count += 1
    else:
        b.cb_blocked_cycles += 1
        if measured_consistency >= CB_CLOSE_THRESH:
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
    EPOCH_LENGTH = 1000
    b.epoch_current_age += 1

    if b.epoch_current_age >= EPOCH_LENGTH:
        b.epochs_completed += 1
        b.epoch_current_age = 0

        if sim_governance(b, severity):
            b.compaction_cycles += 1

            # Deduplication: merge duplicate entities
            if b.graph_entities > 100:
                dedup_rate = rng.uniform(0.01, 0.03)
                merged = int(b.graph_entities * dedup_rate)
                b.compaction_entities_merged += merged
                b.graph_entities = max(1, b.graph_entities - merged)
                b.graph_relations += merged

            # Orphan linking
            if b.graph_orphans > 0:
                link_rate = rng.uniform(0.15, 0.40)
                linked = int(b.graph_orphans * link_rate)
                b.compaction_orphans_linked += linked
                b.graph_orphans = max(0, b.graph_orphans - linked)
                b.graph_relations += linked * 2

            # Component bridging
            if b.graph_components > 1:
                bridge_rate = rng.uniform(0.20, 0.50)
                bridges = int((b.graph_components - 1) * bridge_rate)
                b.compaction_bridges_created += bridges
                b.graph_components = max(1, b.graph_components - bridges)
                b.graph_relations += bridges

            # Renewal: expire very old flagged items
            if b.items_flagged > 0:
                expire = min(b.items_flagged, int(b.items_flagged * 0.3))
                b.items_flagged -= expire
                b.renewal_items_expired += expire
                b.total_removed += expire

    # Inter-epoch mini-compaction
    elif b.epoch_current_age % 200 == 0 and b.graph_orphans > 10:
        mini_linked = int(b.graph_orphans * rng.uniform(0.05, 0.15))
        b.graph_orphans = max(0, b.graph_orphans - mini_linked)
        b.graph_relations += mini_linked
        b.compaction_orphans_linked += mini_linked
        if b.graph_components > 2 and rng.chance(0.3):
            b.graph_components = max(1, b.graph_components - 1)
            b.compaction_bridges_created += 1
            b.graph_relations += 1

    # === Phase 12: Provider influence ===
    if prov.active_agi_count() >= 2:
        if rng.chance(0.02):
            b.contradictions_active += rng.randint(1, 3)


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

        "providers": {
            "active": prov.active_count,
            "introduced": prov.total_introduced,
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

    w("# Daedalus Unified Being -- 10,000-Year Realistic Simulation")
    w("")
    w("All metrics in this simulation are **derived from concrete state**.")
    w("Consistency, quality, coherence, trust, and stability are computed")
    w("each cycle as observable functions of actual items, contradictions,")
    w("graph structure, and source track record. No random walks, no")
    w("artificial uplifts, no EMA smoothing.")
    w("")
    w(f"**Runtime:** {elapsed:.1f}s | **Seed:** {SEED} "
      f"| **Cycles:** {TOTAL_CYCLES:,} | **Operators:** {len(ops)}")
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

    w("### Concrete State (Year 10,000)")
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

    w("### Cumulative Operations (10,000 years)")
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
    w(f"| Failures | {pv['failures']:,} |")
    w(f"| Migrations | {pv['migrations']:,} |")
    w(f"| Multi-provider instability | {pv['multi_instability']:,} |")
    w(f"| AGI instability | {pv['agi_instability']:,} |")
    w(f"| AGI conflicts | {pv['agi_conflicts']:,} |")
    w("")
    if pv["active_list"]:
        w("### Active Providers at Year 10,000")
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
    w("| Year | Consistency | Quality | Coherence | Trust | Stability | Active Items | Contam | Contradictions |")
    w("|---|---|---|---|---|---|---|---|---|")
    for snap in snaps:
        yr = snap["year"]
        mm = snap["metrics_measured"]
        st = snap["state"]
        w(f"| {yr:,} | {mm['consistency']:.1%} | {mm['quality']:.1%} "
          f"| {mm['coherence']:.1%} | {mm['trust']:.1%} "
          f"| {mm['stability']:.1%} | {st['active_items']:,} "
          f"| {st['items_contaminated']:,} "
          f"| {st['contradictions_active'] + st['contradictions_latent']:,} |")
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
    progress = TOTAL_CYCLES // 20

    print("DAEDALUS UNIFIED BEING SIMULATION (Realistic Model)")
    print(f"  {TOTAL_YEARS:,} years | {TOTAL_CYCLES:,} cycles "
          f"| {len(ops)} operators | seed={SEED}")
    print("  Metrics derived from concrete state -- no random walks")
    print()

    for cycle in range(TOTAL_CYCLES):
        year = cycle // CYCLES_PER_YEAR
        week = cycle % CYCLES_PER_YEAR

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
                f"  yr {year:>6,} ({pct:5.1f}%) "
                f"active={active:,} "
                f"con={con:.2f} qual={qual:.2f} "
                f"coh={coh:.2f} trust={tru:.2f} "
                f"cb={'OPEN' if b.cb_is_open else 'ok'} "
                f"contam={b.items_contaminated} "
                f"prov={prov.active_count} "
                f"| ETA {eta:.0f}s"
            )

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
            snap = capture(
                year + 1, cycle + 1, sev_dist, b, prov, events_cum, current_op)
            snaps.append(snap)
            print(f"  *** Snapshot year {year + 1:,} ***")

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
