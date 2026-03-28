# runtime/runtime_main.py

from __future__ import annotations

from typing import Optional, Callable, Dict, Any

from governor.singleton import governor
from runtime.system_health import SystemHealth
from runtime.sho_cycle_orchestrator import SHOCycleOrchestrator
from runtime.runtime_loop import RuntimeLoop
from runtime.patch_engine_adapter import PatchEngineAdapter


def start_runtime(
    fetch_state_fn,
    apply_patch_fn: Optional[Callable] = None,
    fetch_post_state_fn: Optional[Callable] = None,
    fetch_plan_fn: Optional[Callable] = None,
    maintenance_interval_cycles: int = 10,
):
    """
    Entry point for the assistant's continuous improvement runtime.

    When ``apply_patch_fn`` / ``fetch_post_state_fn`` / ``fetch_plan_fn``
    are omitted the runtime falls back to the built-in
    ``runtime.patch_engine`` and ``governor.proposal_manager``.
    """

    if apply_patch_fn is None:
        from runtime.patch_engine import apply_patch
        apply_patch_fn = apply_patch

    if fetch_post_state_fn is None:
        from runtime.patch_engine import fetch_post_state
        fetch_post_state_fn = fetch_post_state

    if fetch_plan_fn is None:
        from runtime.proposal_store import fetch_plan
        fetch_plan_fn = fetch_plan

    health = SystemHealth()

    orchestrator = SHOCycleOrchestrator(
        governor=governor,
        health=health,
    )

    adapter = PatchEngineAdapter(
        apply_patch_fn=apply_patch_fn,
        fetch_post_state_fn=fetch_post_state_fn,
        fetch_plan_fn=fetch_plan_fn,
    )
    adapter.bind(orchestrator)

    loop = RuntimeLoop(
        orchestrator=orchestrator,
        fetch_state_fn=fetch_state_fn,
        maintenance_interval_cycles=maintenance_interval_cycles,
    )

    return loop
