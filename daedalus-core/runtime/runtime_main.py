# runtime/main.py

from __future__ import annotations

from governor.autonomy_governor import AutonomyGovernor
from runtime.system_health import SystemHealth
from runtime.sho_cycle_orchestrator import SHOCycleOrchestrator
from runtime.runtime_loop import RuntimeLoop
from runtime.patch_engine_adapter import PatchEngineAdapter
from runtime.ui_state_bridge import build_ui_state


def start_runtime(
    fetch_state_fn,
    apply_patch_fn,
    fetch_post_state_fn,
    fetch_plan_fn,
    maintenance_interval_cycles: int = 10,
):
    """
    Entry point for the assistant's continuous improvement runtime.
    """

    governor = AutonomyGovernor()
    health = SystemHealth()

    orchestrator = SHOCycleOrchestrator(
        governor=governor,
        health=health,
    )

    # Bind patch engine + plan fetchers
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
