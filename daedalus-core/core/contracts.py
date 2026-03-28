from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict


# ---------- Cockpit / diagnostics ----------

class CockpitSnapshot(TypedDict, total=False):
    user_input: str
    clean_input: str
    parsed_intent: str
    resolver_target: str
    result: str

    nlu_repr: str
    nlu_intent: Optional[str]
    nlu_entities: Optional[Any]
    nlu_confidence: Optional[float]
    nlu_ambiguous: Optional[bool]

    firewall_repr: str
    firewall_allowed: Optional[bool]
    firewall_reason: Optional[str]

    resolved_repr: str
    resolver_rule: Optional[str]
    resolver_fallback: Optional[bool]

    final_repr: str
    handler_name: Optional[str]
    handler_module: Optional[str]

    sanitize_report: Any
    hostility_score: Any

    state_changed: bool
    changed_keys: List[str]

    error_type: str
    error_message: str
    subsystem: str
    pipeline_stage: str


# ---------- Evolution / improvement ----------

@dataclass
class FixRequest:
    target_subsystem: str
    change_type: str          # "bugfix" | "feature" | "refactor" | "reorg"
    severity: str             # "low" | "medium" | "high"
    constraints: Dict[str, Any]
    max_cycles: int
    max_runtime_seconds: int


@dataclass
class ImprovementPlan:
    fix_request: FixRequest
    allowed_modules: List[str]
    forbidden_modules: List[str]
    change_budget_files: int
    change_budget_lines: int
    safety_invariants: List[str]
    night_mode: bool = False
    blocked: bool = False
    block_reason: str = ""


@dataclass
class Patch:
    file_path: str
    description: str
    before: Optional[str]
    after: str
    risk_level: str           # "low" | "medium" | "high"


@dataclass
class CycleResult:
    success: bool
    tests_passed: int
    tests_failed: int
    metrics: Dict[str, Any]
    behavior_snapshot: Dict[str, Any]


@dataclass
class DriftReport:
    code_drift_pct: float
    behavior_drift_pct: float
    positive_change_score: float
    negative_change_score: float
    net_improvement: float
    confidence: float


@dataclass
class CandidateSummary:
    plan: ImprovementPlan
    best_cycle_index: int
    drift_report: DriftReport
    metrics: Dict[str, Any]
    risks: List[str]
    recommendation: str       # "apply" | "reject" | "review"
    vetoed: bool = False
    veto_reason: str = ""


# ---------- Night mode / proposals ----------

@dataclass
class Opportunity:
    target_subsystem: str
    issue_type: str
    severity: str
    frequency: int
    impact_estimate: float


@dataclass
class ImprovementProposal:
    description: str
    target_subsystem: str
    proposal_type: str        # "bugfix" | "optimize" | "new_ability" | "reorg"
    estimated_complexity: str
    risk_level: str
    expected_benefit: float


@dataclass
class NightCandidate:
    proposal: ImprovementProposal
    candidate_summary: CandidateSummary


@dataclass
class NightReport:
    timestamp: str
    opportunities: List[Opportunity]
    proposals: List[ImprovementProposal]
    candidates: List[NightCandidate]


# ---------- Security ----------

@dataclass
class SecurityEvent:
    timestamp: str
    event_type: str          # "integrity_mismatch" | "untracked_change" | "suspicious_pattern" | "unknown_capability"
    severity: str            # "low" | "medium" | "high" | "critical"
    details: Dict[str, Any]
    affected_files: List[str]


@dataclass
class SecurityStatus:
    mode: str                # "normal" | "suspicious" | "locked_down"
    last_events: List[SecurityEvent]
    integrity_ok: bool
    unknown_capabilities_detected: bool
    recommendations: List[str]
