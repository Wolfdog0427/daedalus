from typing import Any
from runtime import integrity_validator, semantic_firewall

class HostileInputRejected(Exception):
    pass

async def hem_process_hostile_input(raw: Any) -> Any:
    # Quarantine + schema + sanitization + cross-check via existing modules
    if not integrity_validator.validate_schema(raw):
        raise HostileInputRejected("schema_invalid")

    sanitized = semantic_firewall.sanitize(raw)

    if not integrity_validator.cross_check(sanitized):
        raise HostileInputRejected("cross_check_failed")

    return sanitized
