# knowledge/action_router.py

"""
Action Router

Maps natural-language console commands to concrete system actions.

This module is intentionally thin: it interprets the user's command,
routes it to the appropriate subsystem (SHO, stability engine, dashboard,
trust scoring, autonomy governor), and returns a human-readable summary.
"""

from __future__ import annotations

from typing import Optional

from knowledge.system_dashboard import dashboard_summary
from knowledge.stability_engine import enforce_stability
from knowledge.trust_scoring import verify_and_ingest

# These subsystems are optional and may evolve over time.
# We import them defensively to avoid hard crashes if they change.
try:
    import knowledge.self_healing_orchestrator as sho
except ImportError:  # pragma: no cover
    sho = None  # type: ignore[assignment]

try:
    import knowledge.autonomy_governor as governor
except ImportError:  # pragma: no cover
    governor = None  # type: ignore[assignment]


# -------------------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------------------

def _normalize(cmd: str) -> str:
    return cmd.strip().lower()


def _extract_after_colon(cmd: str) -> str:
    if ":" in cmd:
        return cmd.split(":", 1)[1].strip()
    return ""


# -------------------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------------------

def route_command(cmd: str, claim: Optional[str] = None) -> str:
    """
    Route a natural-language command to the appropriate subsystem.

    Parameters
    ----------
    cmd:
        The raw command string entered by the user.
    claim:
        Optional extracted claim text (for "verify this:" / "explain this:" patterns).

    Returns
    -------
    str
        A human-readable result string to display in the console.
    """
    norm = _normalize(cmd)

    # ------------------------------------------------------------
    # CONSISTENCY / SHO
    # ------------------------------------------------------------
    if norm.startswith("run a consistency scan") or norm.startswith("run consistency scan") or norm == "consistency scan":
        if sho is not None and hasattr(sho, "run_consistency_scan"):
            result = sho.run_consistency_scan()  # type: ignore[attr-defined]
            return f"[CONSISTENCY SCAN]\n{result}"
        return "[CONSISTENCY SCAN]\nSelf-Healing Orchestrator is not available or not wired with run_consistency_scan()."

    if norm.startswith("evolve concepts") or norm.startswith("run evolution") or norm.startswith("evolve"):
        if sho is not None and hasattr(sho, "run_evolution_cycle"):
            result = sho.run_evolution_cycle()  # type: ignore[attr-defined]
            return f"[EVOLUTION]\n{result}"
        return "[EVOLUTION]\nConcept evolution is not available or not wired with run_evolution_cycle()."

    # ------------------------------------------------------------
    # STABILITY
    # ------------------------------------------------------------
    if norm.startswith("check stability") or norm == "stability":
        stability = enforce_stability()
        score = stability.get("stability_score")
        risk = stability.get("risk")
        notes = stability.get("notes", {})
        return (
            "=== STABILITY CHECK ===\n"
            f"Stability Score: {score}\n"
            f"Risk:            {risk}\n"
            f"Notes:           {notes}\n"
        )

    # ------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------
    if norm.startswith("show dashboard") or norm == "dashboard":
        return dashboard_summary()

    # ------------------------------------------------------------
    # AUTONOMY GOVERNOR
    # ------------------------------------------------------------
    if norm.startswith("open up autonomy") or norm.startswith("open autonomy"):
        if governor is not None and hasattr(governor, "set_mode"):
            governor.set_mode("open")  # type: ignore[attr-defined]
            return "[AUTONOMY] Mode set to 'open'."
        return "[AUTONOMY] Governor module not available or set_mode() missing."

    if norm.startswith("lock down to strict") or norm.startswith("lock down") or norm.startswith("strict mode"):
        if governor is not None and hasattr(governor, "set_mode"):
            governor.set_mode("strict")  # type: ignore[attr-defined]
            return "[AUTONOMY] Mode set to 'strict'."
        return "[AUTONOMY] Governor module not available or set_mode() missing."

    # ------------------------------------------------------------
    # VERIFY / EXPLAIN CLAIMS
    # ------------------------------------------------------------
    if norm.startswith("verify this") or norm.startswith("verify:") or norm.startswith("verify "):
        text = claim or _extract_after_colon(cmd)
        if not text:
            return "[VERIFY] No claim provided."
        item_id = verify_and_ingest(text, source="verified")
        return f"[VERIFY] Claim ingested and marked verified. Item ID: {item_id}"

    if norm.startswith("explain this") or norm.startswith("explain:") or norm.startswith("explain "):
        text = claim or _extract_after_colon(cmd)
        if not text:
            return "[EXPLAIN] No claim provided."
        # For now, we just echo the request; explanation can be delegated to a higher layer.
        return f"[EXPLAIN] Explanation requested for:\n{text}"

    # ------------------------------------------------------------
    # STORAGE / CLEANUP (PLACEHOLDER)
    # ------------------------------------------------------------
    if norm.startswith("clean up storage") or norm.startswith("cleanup storage") or norm.startswith("clean storage"):
        # Placeholder: real implementation would compact logs, prune superseded items, etc.
        return "[STORAGE] Cleanup requested. (No-op placeholder implementation.)"

    # ------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------
    return f"[UNKNOWN COMMAND] I didn't recognize: {cmd!r}"
