# analytics/delta_tier_selector.py

from __future__ import annotations


def choose_tier_from_deltas(
    base_stability_score: float,
    predicted_stability_delta_total: float,
    predicted_risk_delta_total: float,
) -> int:
    """
    Decide tier based primarily on predicted deltas.

    Intuition:
    - If predicted stability gain is strong and risk reduction is good → allow higher tier.
    - If predicted risk delta is bad or stability gain is weak → stay conservative.
    """

    clamped = max(0.0, min(1.0, base_stability_score)) if isinstance(base_stability_score, (int, float)) else 0.0
    if clamped != clamped:  # NaN check
        clamped = 0.0

    if clamped < 0.3:
        tier = 1
    elif clamped < 0.6:
        tier = 2
    else:
        tier = 3

    if predicted_stability_delta_total > 0.1 and predicted_risk_delta_total <= 0:
        tier = min(3, tier + 1)
    elif predicted_stability_delta_total < 0.0:
        tier = max(1, tier - 1)

    if predicted_risk_delta_total > 0.05:
        tier = max(1, tier - 1)

    return tier
