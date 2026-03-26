# knowledge/provider_discovery.py

"""
Provider Discovery

Automatic discovery, capability assessment, selection, and migration
management for LLM/AGI providers across the Daedalus node fabric.

Design principles:
- Daedalus should never require a manual command to connect to a
  provider. Providers are discovered automatically from:
  1. Node fabric registry (nodes advertising LLM capabilities)
  2. Configured endpoint probes (known service addresses)
  3. Operator-registered providers (manual override, always highest priority)
- Each provider is assessed for capabilities (model, context window,
  speed, specializations) and scored for task fitness.
- The system auto-selects the best provider per task type.
- When upgrades or topology changes occur, migration recommendations
  are generated. If the system can execute the migration (same API),
  it does so silently. If not, it notifies the operator.
- Integrates with the node security engine pattern: unknown providers
  start quarantined and must pass a capability probe before activation.

Governance:
- Provider discovery and probing are read-only (Tier 1+).
- Auto-activation of known providers is Tier 2.
- Migration execution is Tier 2 (same API) or Tier 3 (API change).
- Operator is always notified of provider changes.
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


# ------------------------------------------------------------
# PROVIDER CAPABILITY MODEL
# ------------------------------------------------------------

class ProviderStatus(str, Enum):
    DISCOVERED = "discovered"
    PROBING = "probing"
    QUARANTINED = "quarantined"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MIGRATING = "migrating"


class TaskType(str, Enum):
    GENERAL_REASONING = "general_reasoning"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    CLAIM_ASSESSMENT = "claim_assessment"
    ACQUISITION_PLANNING = "acquisition_planning"
    SUMMARIZATION = "summarization"
    CODE_ANALYSIS = "code_analysis"


@dataclass
class ProviderCapabilities:
    model_name: str = ""
    model_version: str = ""
    context_window: int = 4096
    max_output_tokens: int = 2048
    supports_streaming: bool = False
    supports_function_calling: bool = False
    specializations: List[str] = field(default_factory=list)
    speed_tier: str = "standard"  # "fast" | "standard" | "slow"
    cost_tier: str = "standard"  # "free" | "low" | "standard" | "high"
    api_type: str = "openai"  # "openai" | "anthropic" | "local" | "custom"
    node_id: Optional[str] = None
    endpoint: str = ""


@dataclass
class DiscoveredProvider:
    id: str
    name: str
    status: ProviderStatus
    capabilities: ProviderCapabilities
    discovered_at: float = field(default_factory=time.time)
    last_probe_at: float = 0.0
    last_used_at: float = 0.0
    probe_failures: int = 0
    fitness_scores: Dict[str, float] = field(default_factory=dict)
    migration_source: Optional[str] = None
    operator_registered: bool = False


# ------------------------------------------------------------
# DISCOVERY REGISTRY
# ------------------------------------------------------------

class ProviderRegistry:
    """
    Maintains the canonical registry of all known providers,
    their status, capabilities, and fitness scores.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, DiscoveredProvider] = {}
        self._task_assignments: Dict[str, str] = {}
        self._notifications: List[Dict[str, Any]] = []
        self._probe_endpoints: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # Registration
    # --------------------------------------------------------

    def register_discovered(
        self,
        name: str,
        capabilities: ProviderCapabilities,
        source: str = "fabric",
    ) -> DiscoveredProvider:
        """Register a newly discovered provider in quarantine."""
        provider_id = _generate_provider_id(name, capabilities.endpoint)
        provider = DiscoveredProvider(
            id=provider_id,
            name=name,
            status=ProviderStatus.DISCOVERED,
            capabilities=capabilities,
        )
        self._providers[provider_id] = provider
        self._add_notification(
            "provider_discovered",
            f"New provider '{name}' discovered via {source}",
            {"provider_id": provider_id, "model": capabilities.model_name},
        )
        return provider

    def register_operator_provider(
        self,
        name: str,
        capabilities: ProviderCapabilities,
    ) -> DiscoveredProvider:
        """Operator-registered provider: skip quarantine, go active."""
        provider_id = _generate_provider_id(name, capabilities.endpoint)
        provider = DiscoveredProvider(
            id=provider_id,
            name=name,
            status=ProviderStatus.ACTIVE,
            capabilities=capabilities,
            operator_registered=True,
        )
        self._providers[provider_id] = provider
        return provider

    # --------------------------------------------------------
    # Probing
    # --------------------------------------------------------

    def mark_probe_success(self, provider_id: str, latency_ms: float = 0.0) -> None:
        p = self._providers.get(provider_id)
        if not p:
            return
        p.last_probe_at = time.time()
        p.probe_failures = 0
        if p.status in (ProviderStatus.DISCOVERED, ProviderStatus.QUARANTINED):
            p.status = ProviderStatus.ACTIVE
            self._add_notification(
                "provider_activated",
                f"Provider '{p.name}' passed probe and is now active",
                {"provider_id": provider_id, "latency_ms": latency_ms},
            )

    def mark_probe_failure(self, provider_id: str, error: str = "") -> None:
        p = self._providers.get(provider_id)
        if not p:
            return
        p.probe_failures += 1
        p.last_probe_at = time.time()
        if p.probe_failures >= 3:
            p.status = ProviderStatus.QUARANTINED
            self._add_notification(
                "provider_quarantined",
                f"Provider '{p.name}' quarantined after {p.probe_failures} probe failures",
                {"provider_id": provider_id, "error": error},
            )
        elif p.status == ProviderStatus.ACTIVE:
            p.status = ProviderStatus.DEGRADED
            self._add_notification(
                "provider_degraded",
                f"Provider '{p.name}' degraded: {error}",
                {"provider_id": provider_id},
            )

    def mark_offline(self, provider_id: str) -> None:
        p = self._providers.get(provider_id)
        if p:
            p.status = ProviderStatus.OFFLINE
            self._add_notification(
                "provider_offline",
                f"Provider '{p.name}' is offline",
                {"provider_id": provider_id},
            )

    # --------------------------------------------------------
    # Fitness Scoring + Task Assignment
    # --------------------------------------------------------

    def record_call_outcome(self, provider_id: str, success: bool, latency_ms: float = 0.0) -> None:
        """
        Track per-provider call reliability for fitness weighting.
        Sim-fix M1: cascade failure detection — 5 consecutive failures
        triggers auto-degradation.
        """
        p = self._providers.get(provider_id)
        if not p:
            return
        if not hasattr(p, "_call_successes"):
            p._call_successes = 0  # type: ignore[attr-defined]
            p._call_failures = 0  # type: ignore[attr-defined]
            p._consecutive_failures = 0  # type: ignore[attr-defined]
        if success:
            p._call_successes += 1  # type: ignore[attr-defined]
            p._consecutive_failures = 0  # type: ignore[attr-defined]
        else:
            p._call_failures += 1  # type: ignore[attr-defined]
            p._consecutive_failures = getattr(p, "_consecutive_failures", 0) + 1  # type: ignore[attr-defined]
            # M1: cascade failure — 5 consecutive failures auto-degrades
            if p._consecutive_failures >= 5 and p.status == ProviderStatus.ACTIVE:  # type: ignore[attr-defined]
                p.status = ProviderStatus.DEGRADED
                self._add_notification(
                    "provider_cascade_degraded",
                    f"Provider '{p.name}' degraded after {p._consecutive_failures} consecutive failures",
                    {"provider_id": provider_id},
                )
        p.last_used_at = time.time()

    def get_reliability(self, provider_id: str) -> float:
        """Compute reliability ratio (0.0-1.0) for a provider."""
        p = self._providers.get(provider_id)
        if not p:
            return 0.0
        successes = getattr(p, "_call_successes", 0)
        failures = getattr(p, "_call_failures", 0)
        total = successes + failures
        if total < 5:
            return 0.5  # insufficient data, assume neutral
        return successes / total

    def compute_fitness(self, provider_id: str) -> Dict[str, float]:
        """
        Compute fitness scores for each task type.
        Now includes reliability weighting: providers with low
        reliability are penalized, and a minimum reliability floor
        gates task selection entirely.
        """
        p = self._providers.get(provider_id)
        if not p or p.status not in (ProviderStatus.ACTIVE, ProviderStatus.DEGRADED):
            return {}

        caps = p.capabilities
        reliability = self.get_reliability(provider_id)
        RELIABILITY_FLOOR = 0.70  # Sim-fix M1: raised from 0.60

        scores: Dict[str, float] = {}

        for task in TaskType:
            score = 0.5  # baseline

            # Context window matters for reasoning and extraction
            if task in (TaskType.GENERAL_REASONING, TaskType.KNOWLEDGE_EXTRACTION):
                if caps.context_window >= 128000:
                    score += 0.3
                elif caps.context_window >= 32000:
                    score += 0.2
                elif caps.context_window >= 8000:
                    score += 0.1

            # Speed matters for summarization and claim assessment
            if task in (TaskType.SUMMARIZATION, TaskType.CLAIM_ASSESSMENT):
                if caps.speed_tier == "fast":
                    score += 0.2
                elif caps.speed_tier == "slow":
                    score -= 0.1

            # Function calling matters for planning
            if task == TaskType.ACQUISITION_PLANNING and caps.supports_function_calling:
                score += 0.15

            # Specializations boost
            task_keywords = {
                TaskType.CODE_ANALYSIS: ["code", "programming", "analysis"],
                TaskType.KNOWLEDGE_EXTRACTION: ["extraction", "knowledge", "ner"],
                TaskType.SUMMARIZATION: ["summarization", "compression"],
            }
            for keyword in task_keywords.get(task, []):
                if keyword in [s.lower() for s in caps.specializations]:
                    score += 0.15

            # Operator-registered gets a reliability boost
            if p.operator_registered:
                score += 0.1

            # Degraded penalty
            if p.status == ProviderStatus.DEGRADED:
                score *= 0.7

            # Reliability weighting: scale fitness by reliability ratio
            # Below the floor, the provider is not eligible at all
            if reliability < RELIABILITY_FLOOR:
                score = 0.0
            else:
                score *= (0.5 + 0.5 * reliability)

            scores[task.value] = min(1.0, max(0.0, score))

        p.fitness_scores = scores
        return scores

    def select_best_for_task(self, task: TaskType) -> Optional[str]:
        """
        Select the best active provider for a given task type.
        Returns provider_id or None.
        """
        # Check if there's an explicit assignment
        if task.value in self._task_assignments:
            assigned = self._task_assignments[task.value]
            p = self._providers.get(assigned)
            if p and p.status == ProviderStatus.ACTIVE:
                return assigned

        best_id = None
        best_score = -1.0

        for pid, p in self._providers.items():
            if p.status not in (ProviderStatus.ACTIVE, ProviderStatus.DEGRADED):
                continue
            fitness = p.fitness_scores.get(task.value, 0.0)
            if fitness > best_score:
                best_score = fitness
                best_id = pid

        return best_id

    def assign_task(self, task: TaskType, provider_id: str) -> bool:
        """Operator-directed task assignment."""
        if provider_id not in self._providers:
            return False
        self._task_assignments[task.value] = provider_id
        return True

    # --------------------------------------------------------
    # Migration
    # --------------------------------------------------------

    def recommend_migration(
        self,
        old_provider_id: str,
        new_provider_id: str,
    ) -> Dict[str, Any]:
        """
        Recommend migrating from one provider to another.
        If same API type: can auto-migrate. Otherwise: notify operator.
        """
        old_p = self._providers.get(old_provider_id)
        new_p = self._providers.get(new_provider_id)

        if not old_p or not new_p:
            return {"action": "error", "reason": "provider_not_found"}

        same_api = old_p.capabilities.api_type == new_p.capabilities.api_type
        new_is_better = self._is_upgrade(old_p, new_p)

        recommendation: Dict[str, Any] = {
            "old_provider": old_p.name,
            "new_provider": new_p.name,
            "same_api": same_api,
            "is_upgrade": new_is_better,
            "auto_migratable": same_api,
        }

        if same_api and new_is_better:
            recommendation["action"] = "auto_migrate"
            recommendation["reason"] = (
                f"'{new_p.name}' is a direct upgrade over '{old_p.name}' "
                f"with compatible API"
            )
        elif new_is_better:
            recommendation["action"] = "notify_operator"
            recommendation["reason"] = (
                f"'{new_p.name}' is better but uses a different API type "
                f"({new_p.capabilities.api_type} vs {old_p.capabilities.api_type}). "
                f"Operator approval required for migration."
            )
        else:
            recommendation["action"] = "no_action"
            recommendation["reason"] = "Current provider is adequate"

        self._add_notification(
            "migration_recommendation",
            recommendation["reason"],
            recommendation,
        )

        return recommendation

    def execute_migration(self, old_id: str, new_id: str) -> Dict[str, Any]:
        """
        Execute a provider migration. Updates task assignments and
        marks the old provider as migrated.
        """
        old_p = self._providers.get(old_id)
        new_p = self._providers.get(new_id)

        if not old_p or not new_p:
            return {"status": "error", "reason": "provider_not_found"}

        # Reassign all tasks from old to new
        migrated_tasks = []
        for task_key, assigned_id in list(self._task_assignments.items()):
            if assigned_id == old_id:
                self._task_assignments[task_key] = new_id
                migrated_tasks.append(task_key)

        new_p.migration_source = old_id
        old_p.status = ProviderStatus.OFFLINE

        self._add_notification(
            "migration_executed",
            f"Migrated from '{old_p.name}' to '{new_p.name}'",
            {"old_id": old_id, "new_id": new_id, "tasks": migrated_tasks},
        )

        return {
            "status": "migrated",
            "old_provider": old_p.name,
            "new_provider": new_p.name,
            "migrated_tasks": migrated_tasks,
        }

    def _is_upgrade(self, old: DiscoveredProvider, new: DiscoveredProvider) -> bool:
        old_avg = sum(old.fitness_scores.values()) / max(1, len(old.fitness_scores))
        new_avg = sum(new.fitness_scores.values()) / max(1, len(new.fitness_scores))
        return new_avg > old_avg + 0.05

    # --------------------------------------------------------
    # Notifications
    # --------------------------------------------------------

    def _add_notification(self, event_type: str, message: str, data: Dict[str, Any]) -> None:
        self._notifications.append({
            "timestamp": time.time(),
            "type": event_type,
            "message": message,
            "data": data,
            "acknowledged": False,
        })

    def get_notifications(self, unacknowledged_only: bool = True) -> List[Dict[str, Any]]:
        if unacknowledged_only:
            return [n for n in self._notifications if not n["acknowledged"]]
        return list(self._notifications)

    def acknowledge_notification(self, index: int) -> bool:
        if 0 <= index < len(self._notifications):
            self._notifications[index]["acknowledged"] = True
            return True
        return False

    # --------------------------------------------------------
    # Probe Endpoints (configurable scan targets)
    # --------------------------------------------------------

    def add_probe_endpoint(self, endpoint: str, api_type: str = "openai") -> None:
        """Add a known endpoint to scan during discovery cycles."""
        self._probe_endpoints.append({
            "endpoint": endpoint,
            "api_type": api_type,
            "added_at": time.time(),
        })

    def get_probe_endpoints(self) -> List[Dict[str, Any]]:
        return list(self._probe_endpoints)

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    def list_providers(self, status: Optional[ProviderStatus] = None) -> List[Dict[str, Any]]:
        result = []
        for p in self._providers.values():
            if status and p.status != status:
                continue
            result.append(asdict(p))
        return result

    def get_provider(self, provider_id: str) -> Optional[DiscoveredProvider]:
        return self._providers.get(provider_id)

    def get_active_count(self) -> int:
        return sum(
            1 for p in self._providers.values()
            if p.status == ProviderStatus.ACTIVE
        )


# ------------------------------------------------------------
# DISCOVERY CYCLE
# ------------------------------------------------------------

def run_discovery_cycle(
    registry: ProviderRegistry,
    fabric_nodes: Optional[List[Dict[str, Any]]] = None,
    probe_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Run a full provider discovery cycle:
    1. Scan node fabric for LLM/AGI-capable nodes
    2. Probe configured endpoints
    3. Assess capabilities and compute fitness
    4. Generate migration recommendations if better providers found
    5. Auto-activate or notify operator as appropriate

    Args:
        registry: The provider registry to update
        fabric_nodes: Node list from the fabric/presence engine (optional)
        probe_fn: Function to probe an endpoint (optional, for testing)
    """
    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "discovered": 0,
        "probed": 0,
        "activated": 0,
        "migrations_recommended": 0,
        "notifications": [],
    }

    # 1. Scan fabric nodes
    if fabric_nodes:
        for node in fabric_nodes:
            caps = node.get("capabilities", {})
            if not _node_has_llm_capability(caps):
                continue

            name = node.get("name", node.get("nodeId", "unknown"))
            provider_caps = ProviderCapabilities(
                model_name=caps.get("model", ""),
                model_version=caps.get("version", ""),
                context_window=caps.get("context_window", 4096),
                max_output_tokens=caps.get("max_output_tokens", 2048),
                supports_streaming=caps.get("streaming", False),
                supports_function_calling=caps.get("function_calling", False),
                specializations=caps.get("specializations", []),
                speed_tier=caps.get("speed_tier", "standard"),
                api_type=caps.get("api_type", "openai"),
                node_id=node.get("nodeId"),
                endpoint=caps.get("endpoint", ""),
            )

            existing = _find_by_endpoint(registry, provider_caps.endpoint)
            if not existing:
                registry.register_discovered(name, provider_caps, source="fabric")
                report["discovered"] += 1

    # 2. Probe configured endpoints
    for ep_config in registry.get_probe_endpoints():
        endpoint = ep_config["endpoint"]
        existing = _find_by_endpoint(registry, endpoint)

        if existing and existing.status == ProviderStatus.ACTIVE:
            continue

        if probe_fn:
            try:
                probe_result = probe_fn(endpoint)
                if probe_result.get("success"):
                    pid = existing.id if existing else None
                    if not existing:
                        caps = ProviderCapabilities(
                            endpoint=endpoint,
                            api_type=ep_config["api_type"],
                            model_name=probe_result.get("model", ""),
                            context_window=probe_result.get("context_window", 4096),
                        )
                        p = registry.register_discovered(
                            probe_result.get("model", endpoint),
                            caps,
                            source="probe",
                        )
                        pid = p.id

                    if pid:
                        registry.mark_probe_success(pid, probe_result.get("latency_ms", 0))
                        report["probed"] += 1
                        report["activated"] += 1
                else:
                    if existing:
                        registry.mark_probe_failure(existing.id, probe_result.get("error", ""))
                    report["probed"] += 1
            except Exception:
                if existing:
                    registry.mark_probe_failure(existing.id, "probe_exception")
                report["probed"] += 1

    # 3. Compute fitness for all active providers
    for pid in list(registry._providers.keys()):
        p = registry._providers[pid]
        if p.status in (ProviderStatus.ACTIVE, ProviderStatus.DEGRADED):
            registry.compute_fitness(pid)

    # 4. Check for migration opportunities
    for task in TaskType:
        current = registry.select_best_for_task(task)
        if not current:
            continue

        for pid, p in registry._providers.items():
            if pid == current or p.status != ProviderStatus.ACTIVE:
                continue
            current_score = registry._providers[current].fitness_scores.get(task.value, 0)
            new_score = p.fitness_scores.get(task.value, 0)
            if new_score > current_score + 0.15:
                rec = registry.recommend_migration(current, pid)
                if rec.get("action") == "auto_migrate":
                    try:
                        mig = registry.execute_migration(current, pid)
                        report.setdefault("migrations_executed", []).append(mig)
                    except Exception:
                        pass
                    report["migrations_recommended"] += 1
                elif rec.get("action") == "notify_operator":
                    report["migrations_recommended"] += 1

    report["notifications"] = registry.get_notifications(unacknowledged_only=True)
    return report


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def _generate_provider_id(name: str, endpoint: str) -> str:
    raw = f"{name}:{endpoint}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _node_has_llm_capability(caps: Dict[str, Any]) -> bool:
    """Check if a node's capabilities indicate LLM/AGI service."""
    if caps.get("llm") or caps.get("agi"):
        return True
    cap_list = caps.get("capabilities", [])
    llm_keywords = {"llm", "language_model", "reasoning", "agi", "inference"}
    return bool(set(cap_list) & llm_keywords)


def _find_by_endpoint(
    registry: ProviderRegistry,
    endpoint: str,
) -> Optional[DiscoveredProvider]:
    if not endpoint:
        return None
    for p in registry._providers.values():
        if p.capabilities.endpoint == endpoint:
            return p
    return None


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------

provider_registry = ProviderRegistry()
