# governor/rules.py

from __future__ import annotations

from typing import Dict


def decide_base_tier(autonomy_mode: str, locked: bool) -> int:
    """
    Legacy-compatible base tier decision.
    Still usable by any code that expects a base tier.
    """
    if locked:
        return 1

    if autonomy_mode == "strict":
        return 2
    if autonomy_mode == "normal":
        return 3
    if autonomy_mode == "permissive":
        return 3

    return 1


def should_recommend_tier2(
    drift_level: str,
    weakest_risk: str,
    failed_high_level_cycles: int,
) -> bool:
    if drift_level in ("medium", "high"):
        return True
    if weakest_risk in ("medium", "high"):
        return True
    if failed_high_level_cycles > 3:
        return False
    return False


def should_recommend_tier3(
    drift_level: str,
    weakest_risk: str,
    failed_high_level_cycles: int,
    failed_tier2_cycles: int,
    stability_risk: str,
) -> bool:
    if stability_risk == "high":
        return False
    if drift_level == "high" and weakest_risk == "high":
        return True
    if failed_tier2_cycles >= 3 and drift_level in ("medium", "high"):
        return True
    if failed_high_level_cycles > 5:
        return False
    return False


def is_tier3_blocked(
    base_tier: int,
    autonomy_mode: str,
    locked: bool,
    stability_risk: str,
) -> Dict[str, str | bool]:
    if locked:
        return {"blocked": True, "reason": "locked"}
    if stability_risk == "high":
        return {"blocked": True, "reason": "high_stability_risk"}
    if autonomy_mode == "strict" and base_tier < 3:
        return {"blocked": True, "reason": "strict_mode_base_tier_limit"}
    return {"blocked": False, "reason": ""}
