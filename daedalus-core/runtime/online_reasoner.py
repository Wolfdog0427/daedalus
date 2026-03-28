from typing import Any, Dict, List

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

from .offline_reasoner import OfflineReasoner


class OnlineReasoner:
    """
    Online, LLM-backed interpreter.

    For now:
    - Thin wrapper.
    - Delegates to OfflineReasoner so the system stays functional.
    - Later: replace internals with real LLM integration.

    HEM Integration:
    - Enter HEM when online reasoning is invoked (external interaction boundary)
    - Run post-engagement checks after fallback interpretation
    """

    def __init__(self) -> None:
        self._fallback = OfflineReasoner()

    def interpret(
        self,
        user_input: str,
        history: List[Dict[str, Any]] | None,
        state: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:

        hem_maybe_enter(
            trigger_reason="online_reasoner_interpret",
            metadata={"input_preview": user_input[:80]},
        )

        try:
            result = self._fallback.interpret(user_input, state)
        finally:
            try:
                hem_transition_to_postcheck()
            except Exception:
                pass
            try:
                hem_run_post_engagement_checks()
            except Exception:
                pass

        return result
