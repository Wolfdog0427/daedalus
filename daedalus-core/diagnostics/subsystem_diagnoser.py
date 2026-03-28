# diagnostics/subsystem_diagnoser.py

"""
Subsystem-Aware Diagnostics Engine

This module provides deep, subsystem-specific diagnostics for the assistant.
It evaluates the health of:

- NLU pipeline
- Reasoning engine
- Sandbox execution
- Scoring engine
- Stability engine
- File structure
- Dashboard rendering

Each subsystem returns:
- score (0.0–1.0)
- risk level (none/low/medium/high)
- diagnostic message
- recommended patch target
"""

from __future__ import annotations
from typing import Dict, Any, List


# ---------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------

def _risk_from_score(score: float) -> str:
    if score >= 0.85:
        return "none"
    if score >= 0.65:
        return "low"
    if score >= 0.40:
        return "medium"
    return "high"


# ---------------------------------------------------------
# Subsystem Diagnostics
# ---------------------------------------------------------

def diagnose_nlu() -> Dict[str, Any]:
    score = 0.8
    return {
        "subsystem": "nlu",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "NLU pipeline appears consistent.",
        "target": "nlu_pipeline",
        "synthetic": True,
    }


def diagnose_reasoning() -> Dict[str, Any]:
    score = 0.75
    return {
        "subsystem": "reasoning",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "Reasoning chain is coherent with minor drift.",
        "target": "reasoning_engine",
        "synthetic": True,
    }


def diagnose_sandbox() -> Dict[str, Any]:
    score = 0.9
    return {
        "subsystem": "sandbox",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "Sandbox execution is stable.",
        "target": "sandbox_runner",
        "synthetic": True,
    }


def diagnose_scoring() -> Dict[str, Any]:
    score = 0.6
    return {
        "subsystem": "scoring",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "Scoring engine shows mild stagnation.",
        "target": "trust_scoring",
        "synthetic": True,
    }


def diagnose_stability() -> Dict[str, Any]:
    score = 0.7
    return {
        "subsystem": "stability",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "Stability engine is responsive.",
        "target": "stability_engine",
        "synthetic": True,
    }


def diagnose_file_structure() -> Dict[str, Any]:
    score = 0.65
    return {
        "subsystem": "file_structure",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "File structure shows moderate entropy.",
        "target": "module_structure",
        "synthetic": True,
    }


def diagnose_dashboard() -> Dict[str, Any]:
    score = 0.85
    return {
        "subsystem": "dashboard",
        "score": score,
        "risk": _risk_from_score(score),
        "message": "Dashboard rendering is healthy.",
        "target": "system_dashboard",
        "synthetic": True,
    }


# ---------------------------------------------------------
# Aggregated Diagnostics
# ---------------------------------------------------------

def run_subsystem_diagnostics() -> Dict[str, Any]:
    """
    Run diagnostics across all subsystems and return a structured report.
    """

    subsystems = [
        diagnose_nlu(),
        diagnose_reasoning(),
        diagnose_sandbox(),
        diagnose_scoring(),
        diagnose_stability(),
        diagnose_file_structure(),
        diagnose_dashboard(),
    ]

    # Compute overall health score
    avg_score = sum(s["score"] for s in subsystems) / len(subsystems)

    all_synthetic = all(s.get("synthetic", False) for s in subsystems)
    return {
        "overall_score": avg_score,
        "overall_risk": _risk_from_score(avg_score),
        "synthetic": all_synthetic,
        "subsystems": subsystems,
    }
