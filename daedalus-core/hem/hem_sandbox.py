# hem/hem_sandbox.py

"""
HEM Sandbox Bridge — run HEM-related patches in the sandbox.

Delegates to the existing sandbox_runner with the correct
synchronous interface and Dict[str, Any] patch format.
"""

from __future__ import annotations

from typing import Dict, Any

from knowledge.sandbox_runner import run_in_sandbox


def hem_run_in_sandbox(patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a HEM-initiated patch through the knowledge sandbox.

    Parameters
    ----------
    patch : dict
        Patch descriptor with at least {"goal": str, ...}.

    Returns
    -------
    dict
        Sandbox result containing success, diagnostics, stability.
    """
    return run_in_sandbox(
        patch=patch,
        baseline_snapshot_id="hem_baseline",
        strict_safety=True,
    )
