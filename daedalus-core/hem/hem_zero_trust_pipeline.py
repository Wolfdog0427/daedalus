# hem/hem_zero_trust_pipeline.py

"""
HEM Zero-Trust Pipeline — hostile input processing.

Quarantine + integrity validation + semantic firewall filtering
before any hostile input reaches the core system.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.integrity_validator import integrity_validator
from runtime.semantic_firewall import SemanticFirewall


class HostileInputRejected(Exception):
    pass


def hem_process_hostile_input(raw: Any) -> Any:
    """
    Process hostile input through the zero-trust pipeline:
    1. Integrity validation (full system check)
    2. Semantic firewall filtering (intent validation)

    Raises HostileInputRejected if any check fails.
    """
    integrity_result = integrity_validator.validate()
    if not integrity_result.get("valid", False):
        raise HostileInputRejected("integrity_check_failed")

    if isinstance(raw, dict) and "intent" in raw:
        state = raw.get("state", {})
        firewall_result = SemanticFirewall.firewall(raw, state)
        if firewall_result.get("blocked"):
            raise HostileInputRejected("semantic_firewall_blocked")
        return firewall_result.get("sanitized", raw)

    return raw
