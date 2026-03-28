# hem/hem_zero_trust_pipeline.py

"""
HEM Zero-Trust Pipeline — hostile input processing.

Quarantine + integrity validation + semantic firewall filtering
before any hostile input reaches the core system.
"""

from __future__ import annotations

from typing import Any

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
    valid = integrity_result.get("valid", False) if isinstance(integrity_result, dict) else bool(integrity_result)
    if not valid:
        raise HostileInputRejected("integrity_check_failed")

    if isinstance(raw, dict) and "intent" in raw:
        state = raw.get("state") or {}
        try:
            validated = SemanticFirewall.firewall(raw, state)
            return validated
        except ValueError as exc:
            raise HostileInputRejected(f"semantic_firewall_rejected: {exc}") from exc

    return raw
