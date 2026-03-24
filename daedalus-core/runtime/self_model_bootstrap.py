# runtime/self_model_bootstrap.py
"""
Stable entry points for the self-model layer (REPL / internal callers).

Delegates to :mod:`knowledge.self_model` when importable. On import or runtime
failure, returns minimal read-only structures without mutating global state.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def _minimal_self_model() -> Dict[str, Any]:
    """Safe shape when knowledge.self_model cannot be loaded."""
    return {
        "last_updated": None,
        "capabilities": {
            "ingestion": True,
            "retrieval": True,
            "trust_scoring": True,
            "verification": True,
            "reasoning": True,
        },
        "limitations": {
            "self_model_module_unavailable": True,
        },
        "confidence": {
            "knowledge_quality": 0.0,
            "graph_coherence": 0.0,
            "consistency": 0.0,
        },
        "coverage": {
            "entity_count": 0,
            "relation_count": 0,
            "topic_clusters": 0,
        },
        "blind_spots": [],
        "subsystem_health": {},
        "storage": {},
        "trust_distribution": [],
    }


def _minimal_summary() -> Dict[str, Any]:
    return {
        "knowledge_quality": 0.0,
        "graph_coherence": 0.0,
        "consistency": 0.0,
        "entity_count": 0,
        "relation_count": 0,
        "topic_clusters": 0,
        "blind_spots": [],
        "storage_used": None,
        "storage_ratio": None,
        "note": "Self-model summary unavailable (knowledge.self_model not loaded).",
    }


def get_self_model() -> Dict[str, Any]:
    """
    Return the current self-model dict, or a minimal bootstrap dict.

    Matches :func:`knowledge.self_model.get_self_model` return shape when delegated.
    """
    try:
        from knowledge.self_model import get_self_model as _gsm

        return _gsm()
    except Exception:
        return _minimal_self_model()


def get_self_summary() -> Dict[str, Any]:
    """
    Structured summary of self-understanding.

    Delegates to :func:`knowledge.self_model.summarize_self_model` when available.
    """
    try:
        from knowledge.self_model import summarize_self_model

        return summarize_self_model()
    except Exception:
        return _minimal_summary()


def summarize_self() -> str:
    """Short human-readable / JSON snapshot for REPL-style output."""
    try:
        from knowledge.self_model import summarize_self_model

        return json.dumps(summarize_self_model(), indent=2, default=str)
    except Exception:
        return (
            "Self-model summary unavailable (bootstrap fallback).\n"
            + json.dumps(_minimal_summary(), indent=2, default=str)
        )


def get_capabilities_summary() -> Dict[str, Any]:
    """Thin view of capability flags from the current self-model snapshot."""
    try:
        m = get_self_model()
        caps = m.get("capabilities", {})
        return {"status": "ok", "capabilities": caps}
    except Exception:
        return {"status": "error", "capabilities": {}}
