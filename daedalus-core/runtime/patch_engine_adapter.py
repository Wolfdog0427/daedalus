# runtime/patch_engine_adapter.py

from __future__ import annotations

from typing import Dict, Any, Callable


class PatchEngineAdapter:
    """
    Thin adapter that exposes your patch engine to the SHO orchestrator.
    """

    def __init__(
        self,
        apply_patch_fn: Callable[[str], Dict[str, Any]],
        fetch_post_state_fn: Callable[[], Dict[str, Any]],
        fetch_plan_fn: Callable[[str], Dict[str, Any]],
    ) -> None:
        self.apply_patch_fn = apply_patch_fn
        self.fetch_post_state_fn = fetch_post_state_fn
        self.fetch_plan_fn = fetch_plan_fn

    def bind(self, orchestrator) -> None:
        orchestrator.apply_patch_fn = self.apply_patch_fn
        orchestrator.fetch_post_state_fn = self.fetch_post_state_fn
        orchestrator.fetch_plan_fn = self.fetch_plan_fn
