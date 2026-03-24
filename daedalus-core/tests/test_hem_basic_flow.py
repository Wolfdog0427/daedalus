from hem.hem_state_machine import (
    HEMState,
    hem_get_state,
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)
from hem import hem_snapshot_bridge, hem_drift_bridge


def test_hem_no_reentry_from_non_normal(monkeypatch):
    from hem import hem_state_machine
    hem_state_machine._current_state = HEMState.HEM_ACTIVE

    hem_maybe_enter("test_reentry")
    assert hem_get_state() == HEMState.HEM_ACTIVE


def test_hem_happy_path(monkeypatch):
    from hem import hem_state_machine
    hem_state_machine._current_state = HEMState.NORMAL_MODE

    called_snapshot = {}
    def fake_take_snapshot():
        called_snapshot["called"] = True
        return "snap-123"

    monkeypatch.setattr(
        hem_snapshot_bridge,
        "hem_take_snapshot",
        fake_take_snapshot,
    )

    def fake_post_checks():
        return True

    monkeypatch.setattr(
        hem_drift_bridge,
        "hem_run_post_engagement_checks",
        fake_post_checks,
    )

    hem_maybe_enter("test_happy")
    assert hem_get_state() == HEMState.HEM_ACTIVE
    assert called_snapshot.get("called") is True

    hem_transition_to_postcheck()
    assert hem_get_state() == HEMState.HEM_POSTCHECK

    hem_run_post_engagement_checks()
    assert hem_get_state() == HEMState.NORMAL_MODE


def test_hem_drift_triggers_rollback(monkeypatch):
    from hem import hem_state_machine
    hem_state_machine._current_state = HEMState.NORMAL_MODE

    events = {"snapshot": False, "rollback": False}

    def fake_take_snapshot():
        events["snapshot"] = True
        return "snap-xyz"

    def fake_rollback():
        events["rollback"] = True

    monkeypatch.setattr(
        hem_snapshot_bridge,
        "hem_take_snapshot",
        fake_take_snapshot,
    )
    monkeypatch.setattr(
        hem_snapshot_bridge,
        "hem_rollback_to",
        fake_rollback,
    )

    def fake_post_checks():
        return False

    monkeypatch.setattr(
        hem_drift_bridge,
        "hem_run_post_engagement_checks",
        fake_post_checks,
    )

    hem_maybe_enter("test_drift")
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()

    assert events["snapshot"] is True
    assert events["rollback"] is True
    assert hem_get_state() == HEMState.NORMAL_MODE
