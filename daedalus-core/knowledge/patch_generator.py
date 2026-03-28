# knowledge/patch_generator.py

"""
Drift- and subsystem-aware Patch Generator.
"""

from __future__ import annotations

from typing import List, Dict, Any
import uuid


def _weakest_subsystem(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    subs = diagnostics.get("subsystems") or []
    if not subs:
        return {
            "subsystem": "global",
            "score": 0.7,
            "risk": "low",
            "message": "No subsystem diagnostics available.",
            "target": "global_system",
        }
    return min(subs, key=lambda s: s.get("score", 1.0))


def _stability_patch(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    weakest = _weakest_subsystem(diagnostics)
    return {
        "id": f"patch-{uuid.uuid4()}",
        "goal": "stability reinforcement",
        "strategy": "stability_mode",
        "notes": {
            "reason": "System drift is none; reinforcing stable behavior.",
            "weakest_subsystem": weakest["subsystem"],
            "diagnostics_hint": diagnostics,
            "stability_hint": "avoid structural changes",
        },
        "actions": [
            {"type": "refactor", "target": "low-risk modules"},
            {"type": "cleanup", "target": "unused code paths"},
            {"type": "optimize", "target": "safe micro-optimizations"},
        ],
    }


def _normal_patch(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    weakest = _weakest_subsystem(diagnostics)
    return {
        "id": f"patch-{uuid.uuid4()}",
        "goal": "general improvement",
        "strategy": "normal_mode",
        "notes": {
            "reason": "Low drift; normal improvement cycle.",
            "weakest_subsystem": weakest["subsystem"],
            "diagnostics_hint": diagnostics,
        },
        "actions": [
            {"type": "refactor", "target": weakest.get("target", weakest.get("subsystem", "unknown"))},
            {"type": "improve", "target": "reasoning clarity"},
        ],
    }


def _adaptive_patch(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    weakest = _weakest_subsystem(diagnostics)
    return {
        "id": f"patch-{uuid.uuid4()}",
        "goal": "adaptive improvement",
        "strategy": "adaptive_mode",
        "notes": {
            "reason": "Medium drift; exploring new strategies.",
            "weakest_subsystem": weakest["subsystem"],
            "diagnostics_hint": diagnostics,
            "novelty": "high",
        },
        "actions": [
            {"type": "explore", "target": weakest.get("target", weakest.get("subsystem", "unknown"))},
            {"type": "restructure", "target": "modular boundaries"},
            {"type": "enhance", "target": "diagnostics depth"},
        ],
    }


def _recovery_patch(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    weakest = _weakest_subsystem(diagnostics)
    return {
        "id": f"patch-{uuid.uuid4()}",
        "goal": "regression recovery",
        "strategy": "recovery_mode",
        "notes": {
            "reason": "High drift; system instability detected.",
            "weakest_subsystem": weakest["subsystem"],
            "diagnostics_hint": diagnostics,
            "stability_hint": "prioritize safety",
        },
        "actions": [
            {"type": "rollback", "target": weakest.get("target", weakest.get("subsystem", "unknown"))},
            {"type": "tighten", "target": "safety constraints"},
            {"type": "repair", "target": "diagnosed weak areas"},
        ],
    }


def generate_patches_for_goal(
    goal: str,
    diagnostics: Dict[str, Any],
    stability: Dict[str, Any],
    max_candidates: int = 3,
    exploration: str = "medium",
) -> List[Dict[str, Any]]:
    """
    Generate drift- and subsystem-aware patches.
    """

    patches: List[Dict[str, Any]] = []

    if exploration == "minimal":
        for _ in range(max_candidates):
            patches.append(_recovery_patch(diagnostics))
    elif exploration == "low":
        for _ in range(max_candidates):
            patches.append(_stability_patch(diagnostics))
    elif exploration == "medium":
        for _ in range(max_candidates):
            patches.append(_normal_patch(diagnostics))
    elif exploration == "high":
        for _ in range(max_candidates):
            patches.append(_adaptive_patch(diagnostics))
    else:
        for _ in range(max_candidates):
            patches.append(_normal_patch(diagnostics))

    if stability.get("strict"):
        for p in patches:
            p.setdefault("notes", {})
            p["notes"]["strict_safety"] = True
            p["actions"].append({"type": "verify", "target": "safety invariants"})

    return patches
