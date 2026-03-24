# runtime/notification_hooks.py

"""
Notification Hooks

This module defines all event → notification mappings.
It is called by:
- SHO Patch Flow
- Autonomy Governor
- Patch History Manager
- Diagnostics
- System Health Dashboard

It pushes notifications into the Notification Center.

This module does NOT perform any self-modification.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.notification_center import push_notification


# -----------------------------
# Governor-related notifications
# -----------------------------

def notify_tier3_proposal_created(proposal_id: str, subsystem: str) -> None:
    push_notification(
        category="tier3",
        message=f"Tier 3 proposal created for subsystem '{subsystem}'. Approval required.",
        metadata={"proposal_id": proposal_id, "subsystem": subsystem},
    )


def notify_escalation_recommended(tier: int, reason: str) -> None:
    push_notification(
        category="escalation",
        message=f"Escalation to Tier {tier} recommended.",
        metadata={"reason": reason},
    )


# -----------------------------
# Patch-related notifications
# -----------------------------

def notify_patch_success(cycle_id: str, tier: int) -> None:
    push_notification(
        category="patch_success",
        message=f"Patch succeeded in cycle {cycle_id} (Tier {tier}).",
        metadata={"cycle_id": cycle_id, "tier": tier},
    )


def notify_patch_failure(cycle_id: str, tier: int, details: Dict[str, Any]) -> None:
    push_notification(
        category="patch_failure",
        message=f"Patch FAILED in cycle {cycle_id} (Tier {tier}).",
        metadata={"cycle_id": cycle_id, "tier": tier, "details": details},
    )


def notify_patch_reverted(cycle_id: str, reason: str) -> None:
    push_notification(
        category="patch_reverted",
        message=f"Patch reverted in cycle {cycle_id}.",
        metadata={"cycle_id": cycle_id, "reason": reason},
    )


# -----------------------------
# Drift & Stability notifications
# -----------------------------

def notify_drift_high(level: str, score: float) -> None:
    push_notification(
        category="drift",
        message=f"Drift level is HIGH ({level}, score={score}).",
        metadata={"level": level, "score": score},
    )


def notify_stability_low(risk: str, score: float) -> None:
    push_notification(
        category="stability",
        message=f"System stability is LOW (risk={risk}, score={score}).",
        metadata={"risk": risk, "score": score},
    )


# -----------------------------
# Autonomy & Lock notifications
# -----------------------------

def notify_autonomy_mode_changed(mode: str) -> None:
    push_notification(
        category="autonomy",
        message=f"Autonomy mode changed to '{mode}'.",
        metadata={"mode": mode},
    )


def notify_system_locked() -> None:
    push_notification(
        category="lock",
        message="System has been LOCKED.",
        metadata={},
    )


def notify_system_unlocked() -> None:
    push_notification(
        category="lock",
        message="System has been UNLOCKED.",
        metadata={},
    )
