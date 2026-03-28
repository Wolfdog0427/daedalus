# knowledge/llm_adapter.py

"""
LLM Adapter

Provides a modular, provider-agnostic interface for connecting any
LLM or AGI system to Daedalus's cognitive subsystems.

Design:
- LLMProvider is the minimal protocol any reasoning backend must satisfy.
- LLMAdapter is the singleton registry that routes calls to the active provider.
- Higher-level cognitive methods (reason, summarize, extract, plan) are built
  on top of the raw completion interface, so providers only need to implement
  one method.
- When no provider is connected, all calls degrade gracefully with structured
  "unavailable" responses. The symbolic reasoning path remains fully functional.

Integration points:
- CuriosityEngine uses this for domain assessment and acquisition planning.
- ReasoningEngine can delegate uncertain claims here for deeper analysis.
- Any future module can call llm_adapter.complete() without caring which
  backend is behind it.

Operator control:
- Operator can register/remove providers and select the active one.
- System can auto-select based on availability if operator has not set a
  preference.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable


# ------------------------------------------------------------
# PROVIDER PROTOCOL
# ------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """
    Minimal interface that any LLM or AGI backend must satisfy.

    Implementors only need three methods:
    - complete(): the core reasoning capability
    - is_available(): health check
    - provider_info(): metadata about the provider
    """

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion for the given prompt."""
        ...

    def is_available(self) -> bool:
        """Return True if the provider is ready to accept requests."""
        ...

    def provider_info(self) -> Dict[str, Any]:
        """Return metadata: name, model, version, capabilities."""
        ...


# ------------------------------------------------------------
# NULL PROVIDER (graceful degradation)
# ------------------------------------------------------------

class NullProvider:
    """
    Fallback provider when no LLM is connected.
    Returns structured unavailability signals so callers can
    degrade to symbolic reasoning paths.
    """

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        return ""

    def is_available(self) -> bool:
        return False

    def provider_info(self) -> Dict[str, Any]:
        return {
            "name": "null",
            "model": "none",
            "version": "0.0.0",
            "capabilities": [],
        }


_NULL_PROVIDER = NullProvider()


# ------------------------------------------------------------
# LLM ADAPTER (singleton registry + routing)
# ------------------------------------------------------------

class LLMAdapter:
    """
    Central registry and routing layer for LLM/AGI providers.

    Responsibilities:
    - Register and manage multiple providers
    - Route calls to the active provider (operator-selected or auto-selected)
    - Provide higher-level cognitive methods built on raw completion
    - Degrade gracefully when no provider is available
    - Enforce operator query priority over background (ABP) queries
    """

    def __init__(self) -> None:
        self._providers: Dict[str, LLMProvider] = {}
        self._active_name: Optional[str] = None
        self._operator_query_active: bool = False
        self._abp_paused: bool = False

    # ------------------------------------------------------------
    # Provider Management
    # ------------------------------------------------------------

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider

    def remove_provider(self, name: str) -> bool:
        if name not in self._providers:
            return False
        del self._providers[name]
        if self._active_name == name:
            self._active_name = None
        return True

    def set_active_provider(self, name: str) -> bool:
        """Operator-directed provider selection."""
        if name not in self._providers:
            return False
        self._active_name = name
        return True

    def get_active_provider(self) -> LLMProvider:
        """
        Returns the active provider. Selection order:
        1. Operator-selected provider (if set and available)
        2. First available provider
        3. NullProvider (graceful degradation)
        """
        if self._active_name and self._active_name in self._providers:
            provider = self._providers[self._active_name]
            if provider.is_available():
                return provider

        for provider in self._providers.values():
            if provider.is_available():
                return provider

        return _NULL_PROVIDER

    def list_providers(self) -> List[Dict[str, Any]]:
        result = []
        for name, provider in self._providers.items():
            info = provider.provider_info()
            info["registered_name"] = name
            info["is_active"] = name == self._active_name
            info["available"] = provider.is_available()
            result.append(info)
        return result

    def is_available(self) -> bool:
        return self.get_active_provider().is_available()

    # ------------------------------------------------------------
    # Task-Aware Provider Selection (base fallback)
    # ------------------------------------------------------------

    def select_for_task(self, task_type: str) -> LLMProvider:
        """Base implementation: no task-aware routing, use active provider."""
        return self.get_active_provider()

    # ------------------------------------------------------------
    # Operator Priority
    # ------------------------------------------------------------

    def begin_operator_query(self) -> None:
        """Signal that an operator query is in progress (foreground priority)."""
        self._operator_query_active = True
        self._abp_paused = True

    def end_operator_query(self) -> None:
        """Signal that the operator query completed; ABP may resume."""
        self._operator_query_active = False
        self._abp_paused = False

    def is_operator_query_active(self) -> bool:
        return self._operator_query_active

    def is_abp_paused(self) -> bool:
        """ABP background queries should check this before calling complete()."""
        return self._abp_paused

    def complete_for_operator(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Operator-priority completion: pauses ABP, runs query, resumes."""
        self.begin_operator_query()
        try:
            return self.complete(prompt, system_prompt, max_tokens, temperature)
        finally:
            self.end_operator_query()

    def complete_for_abp(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Background ABP completion: yields if operator query is active."""
        if self._abp_paused:
            return ""
        return self.complete(prompt, system_prompt, max_tokens, temperature)

    # ------------------------------------------------------------
    # Core Completion (routes to active provider)
    # ------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        try:
            return self.get_active_provider().complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception:
            return ""

    # ------------------------------------------------------------
    # Task-Aware Completion
    # ------------------------------------------------------------

    def complete_for_task(
        self,
        prompt: str,
        task_type: str = "general",
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Route through select_for_task when task_type is meaningful."""
        try:
            provider = self.select_for_task(task_type)
            return provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception:
            return self.complete(prompt, system_prompt, max_tokens, temperature)

    # ------------------------------------------------------------
    # Higher-Level Cognitive Methods
    # ------------------------------------------------------------

    def reason_about_claim(self, claim: str, context: str = "") -> Dict[str, Any]:
        """
        Ask the LLM to reason about a claim given context.
        Returns structured assessment or unavailable signal.
        """
        if not self.is_available():
            return {"available": False, "assessment": None}

        prompt = (
            f"Given the following context:\n{context}\n\n"
            f"Assess the following claim:\n{claim}\n\n"
            "Respond with: supported, contradicted, or uncertain, "
            "followed by a brief explanation."
        )
        raw = self.complete_for_task(prompt, task_type="general_reasoning",
                                     system_prompt="You are a precise reasoning engine.")
        return {"available": True, "assessment": raw, "claim": claim}

    def extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts/topics from text."""
        if not self.is_available():
            return []

        prompt = (
            f"Extract the key concepts, topics, and domain areas from "
            f"this text. Return one concept per line, no numbering:\n\n{text}"
        )
        raw = self.complete_for_task(prompt, task_type="knowledge_extraction",
                                     system_prompt="You extract structured knowledge.")
        return [line.strip() for line in raw.strip().split("\n") if line.strip()]

    def assess_domain_relevance(
        self,
        domain: str,
        existing_entities: List[str],
        blind_spots: List[str],
    ) -> Dict[str, Any]:
        """
        Assess how relevant a knowledge domain is given current
        knowledge graph entities and identified blind spots.
        """
        if not self.is_available():
            return {"available": False, "relevance": 0.0, "rationale": ""}

        entity_sample = ", ".join(existing_entities[:30])
        spot_sample = ", ".join(blind_spots[:20])

        prompt = (
            f"Domain to assess: {domain}\n\n"
            f"Current knowledge entities (sample): {entity_sample}\n\n"
            f"Identified blind spots: {spot_sample}\n\n"
            "On a scale of 0.0 to 1.0, how relevant is learning about "
            "this domain to strengthen the existing knowledge base? "
            "Respond with the score on the first line, then a brief rationale."
        )
        raw = self.complete_for_task(prompt, task_type="reasoning",
                                     system_prompt="You assess knowledge relevance.")

        lines = raw.strip().split("\n", 1)
        try:
            score = float(lines[0].strip())
            score = max(0.0, min(1.0, score))
        except (ValueError, IndexError):
            score = 0.5
        rationale = lines[1].strip() if len(lines) > 1 else ""

        return {"available": True, "relevance": score, "rationale": rationale}

    def generate_acquisition_plan(
        self,
        topic: str,
        existing_knowledge_summary: str,
        gap_description: str,
    ) -> Dict[str, Any]:
        """
        Generate a structured knowledge acquisition plan for a topic.
        """
        if not self.is_available():
            return {"available": False, "plan": None}

        prompt = (
            f"Topic to learn: {topic}\n\n"
            f"Existing knowledge summary:\n{existing_knowledge_summary}\n\n"
            f"Identified gap:\n{gap_description}\n\n"
            "Create a structured learning plan with 3-5 phases. "
            "For each phase, list:\n"
            "- Phase name\n"
            "- Key concepts to acquire\n"
            "- How this builds on the previous phase\n"
            "Format each phase on its own line as: "
            "PHASE: name | CONCEPTS: a, b, c | BUILDS_ON: description"
        )
        raw = self.complete_for_task(
            prompt,
            task_type="acquisition_planning",
            system_prompt="You create structured knowledge acquisition plans.",
            max_tokens=1024,
        )

        phases = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line or "PHASE:" not in line:
                continue
            phase: Dict[str, Any] = {"raw": line}
            if "PHASE:" in line:
                parts = line.split("|")
                for part in parts:
                    part = part.strip()
                    if part.startswith("PHASE:"):
                        phase["name"] = part[6:].strip()
                    elif part.startswith("CONCEPTS:"):
                        phase["concepts"] = [
                            c.strip() for c in part[9:].split(",")
                        ]
                    elif part.startswith("BUILDS_ON:"):
                        phase["builds_on"] = part[10:].strip()
            phases.append(phase)

        return {"available": True, "topic": topic, "phases": phases}

    def summarize_for_ingestion(self, text: str, max_length: int = 500) -> str:
        """
        Summarize text into a form suitable for knowledge ingestion.
        Preserves factual density while reducing noise.
        """
        if not self.is_available():
            return text[:max_length]

        prompt = (
            f"Summarize the following text into a dense, factual form "
            f"suitable for a knowledge base. Preserve key facts, entities, "
            f"and relationships. Maximum {max_length} characters:\n\n{text}"
        )
        return self.complete(prompt, max_tokens=max_length // 2)


# ------------------------------------------------------------
# AUTO-DISCOVERY INTEGRATION
# ------------------------------------------------------------

class DiscoveryAwareLLMAdapter(LLMAdapter):
    """
    Extends LLMAdapter with automatic provider discovery.
    Periodically checks the provider registry for new/better
    providers and activates them without operator intervention.
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_discovery_check: float = 0.0
        self._discovery_interval_sec: float = 60.0
        self._auto_discovery_enabled: bool = True

    def set_auto_discovery(self, enabled: bool) -> None:
        self._auto_discovery_enabled = enabled

    def set_discovery_interval(self, seconds: float) -> None:
        self._discovery_interval_sec = max(10.0, seconds)

    def _maybe_run_discovery(self) -> None:
        """Check for new providers if enough time has elapsed."""
        if not self._auto_discovery_enabled:
            return
        now = time.time()
        if now - self._last_discovery_check < self._discovery_interval_sec:
            return
        self._last_discovery_check = now
        self._sync_from_registry()

    def _sync_from_registry(self) -> None:
        """
        Sync active providers from the discovery registry into
        this adapter's provider map. New providers are registered
        automatically; offline providers are removed.
        """
        try:
            from knowledge.provider_discovery import provider_registry, ProviderStatus
        except ImportError:
            return

        for p in provider_registry._providers.values():
            registered_name = f"discovered:{p.id}"

            if p.status == ProviderStatus.ACTIVE:
                if registered_name not in self._providers:
                    bridge = _RegistryBridgeProvider(p)
                    self.register_provider(registered_name, bridge)

            elif p.status in (ProviderStatus.OFFLINE, ProviderStatus.QUARANTINED):
                if registered_name in self._providers:
                    self.remove_provider(registered_name)

    def get_active_provider(self) -> "LLMProvider":
        """Override: check discovery before selecting."""
        self._maybe_run_discovery()
        return super().get_active_provider()

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Surface provider discovery notifications to the operator."""
        try:
            from knowledge.provider_discovery import provider_registry
            return provider_registry.get_notifications(unacknowledged_only=True)
        except ImportError:
            return []

    def select_for_task(self, task_type: str) -> "LLMProvider":
        """
        Select the best provider for a specific task type.
        Uses fitness scoring from the discovery registry.
        Falls back to the default active provider.
        """
        self._maybe_run_discovery()

        try:
            from knowledge.provider_discovery import (
                provider_registry, TaskType, ProviderStatus,
            )
            task = TaskType(task_type)
            best_id = provider_registry.select_best_for_task(task)
            if best_id:
                p = provider_registry.get_provider(best_id)
                if p and p.status == ProviderStatus.ACTIVE:
                    registered_name = f"discovered:{best_id}"
                    if registered_name in self._providers:
                        provider = self._providers[registered_name]
                        if provider.is_available():
                            return provider
        except (ImportError, ValueError):
            pass

        return self.get_active_provider()


class _RegistryBridgeProvider:
    """
    Bridges a DiscoveredProvider from the registry into the
    LLMProvider protocol. Routes completion requests to the
    provider's endpoint using the appropriate API client.
    """

    def __init__(self, discovered: Any) -> None:
        self._discovered = discovered

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        caps = self._discovered.capabilities
        endpoint = caps.endpoint
        api_type = caps.api_type

        if not endpoint:
            return ""

        try:
            return _call_provider_endpoint(
                endpoint=endpoint,
                api_type=api_type,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model=caps.model_name,
            )
        except Exception:
            return ""

    def is_available(self) -> bool:
        try:
            from knowledge.provider_discovery import ProviderStatus
            return self._discovered.status == ProviderStatus.ACTIVE
        except ImportError:
            return False

    def provider_info(self) -> Dict[str, Any]:
        caps = self._discovered.capabilities
        return {
            "name": self._discovered.name,
            "model": caps.model_name,
            "version": caps.model_version,
            "capabilities": caps.specializations,
            "api_type": caps.api_type,
            "node_id": caps.node_id,
            "endpoint": caps.endpoint,
        }


def _call_provider_endpoint(
    endpoint: str,
    api_type: str,
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    model: str = "",
) -> str:
    """
    Universal provider call. Supports OpenAI-compatible and
    Anthropic-compatible APIs. Extensible for custom protocols.
    """
    import json as _json

    try:
        import requests
    except ImportError:
        return ""

    try:
        if api_type in ("openai", "local"):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if model:
                payload["model"] = model

            url = endpoint.rstrip("/")
            if not url.endswith("/chat/completions"):
                url += "/chat/completions"

            resp = requests.post(url, json=payload, timeout=60)
            if resp.ok:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return ""

        if api_type == "anthropic":
            payload = {
                "prompt": f"\n\nHuman: {system_prompt}\n{prompt}\n\nAssistant:",
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature,
            }
            if model:
                payload["model"] = model

            resp = requests.post(endpoint, json=payload, timeout=60)
            if resp.ok:
                data = resp.json()
                return data.get("completion", "")
            return ""

    except Exception:
        return ""

    return ""


# ------------------------------------------------------------
# GLOBAL INSTANCE (discovery-aware)
# ------------------------------------------------------------

llm_adapter = DiscoveryAwareLLMAdapter()
