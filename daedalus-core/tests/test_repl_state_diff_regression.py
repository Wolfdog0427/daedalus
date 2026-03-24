# tests/test_repl_state_diff_regression.py

import pytest
import copy

from runtime.repl import _process_line, build_assistant
from runtime.context_resolver import ContextResolver
from runtime.contextual_resolver import ContextualResolver
from runtime.state_store import StateStore
from runtime.plan_renderer import PlanRenderer
from runtime.goal_dashboard_renderer import GoalDashboardRenderer


# ------------------------------------------------------------
# FIXTURE: Full REPL environment
# ------------------------------------------------------------

@pytest.fixture
def env():
    store = StateStore()
    state = store.state

    execution, goal_manager = build_assistant()
    context_resolver = ContextResolver()
    contextual_resolver = ContextualResolver()

    plan_renderer = PlanRenderer()
    dashboard = GoalDashboardRenderer()

    class DebugState:
        nlu = False
        exec = False

    debug_state = DebugState()

    return {
        "state": state,
        "store": store,
        "execution": execution,
        "goal_manager": goal_manager,
        "context_resolver": context_resolver,
        "contextual_resolver": contextual_resolver,
        "plan_renderer": plan_renderer,
        "dashboard": dashboard,
        "debug_state": debug_state,
        "plan_mode": "pretty",
        "dashboard_sort": "created",
        "dashboard_filter": "all",
    }


def run(env, text):
    """Run a single REPL line through the full pipeline."""
    return _process_line(
        text,
        env["state"],
        env["execution"],
        env["goal_manager"],
        env["context_resolver"],
        env["contextual_resolver"],
        env["debug_state"],
        env["store"],
        env["plan_renderer"],
        env["dashboard"],
        env["plan_mode"],
        env["dashboard_sort"],
        env["dashboard_filter"],
    )


# ------------------------------------------------------------
# DIFF HELPER
# ------------------------------------------------------------

def diff(before, after):
    """Return a structural diff between two dicts."""
    added = {}
    removed = {}
    changed = {}

    before_keys = set(before.keys())
    after_keys = set(after.keys())

    for k in before_keys - after_keys:
        removed[k] = before[k]

    for k in after_keys - before_keys:
        added[k] = after[k]

    for k in before_keys & after_keys:
        if before[k] != after[k]:
            changed[k] = (before[k], after[k])

    return added, removed, changed


# ------------------------------------------------------------
# TESTS
# ------------------------------------------------------------

def test_add_goal_state_diff(env, capsys):
    before = copy.deepcopy(env["state"])
    run(env, "add goal TestGoal")
    after = env["state"]

    added, removed, changed = diff(before, after)

    # Only goals_tree and history should change
    assert "goals_tree" in changed
    assert "history" in changed or "history" in added
    assert len(removed) == 0


def test_add_step_state_diff(env, capsys):
    run(env, "add goal StepGoal")

    before = copy.deepcopy(env["state"])
    run(env, "add step StepOne")
    after = env["state"]

    added, removed, changed = diff(before, after)

    assert "goals_tree" in changed
    assert len(removed) == 0


def test_complete_step_state_diff(env, capsys):
    run(env, "add goal DiffGoal")
    run(env, "add step A")
    run(env, "add step B")

    before = copy.deepcopy(env["state"])
    run(env, "complete the step")  # vague reference
    after = env["state"]

    added, removed, changed = diff(before, after)

    assert "goals_tree" in changed
    assert "last_step_referenced" in changed
    assert len(removed) == 0


def test_undo_redo_exact_state_restore(env, capsys):
    run(env, "add goal UndoGoal")
    run(env, "add step X")

    before = copy.deepcopy(env["state"])
    run(env, "undo")
    run(env, "redo")
    after = env["state"]

    assert before == after


def test_checkpoint_restore_exact_state(env, capsys):
    run(env, "add goal CPGoal")
    run(env, "add step CP1")

    run(env, "save checkpoint cp1")

    run(env, "add step CP2")
    run(env, "add step CP3")

    run(env, "restore checkpoint cp1")

    state = env["state"]
    steps = state["goals_tree"][0]["steps"]

    assert len(steps) == 1
    assert steps[0]["text"] == "CP1"


def test_watchpoint_diff_accuracy(env, capsys):
    run(env, "watch goals_tree")

    before = copy.deepcopy(env["state"])
    run(env, "add goal WatchGoal")
    after = env["state"]

    entry = env["store"].history[-1]
    changes = entry.get("watch_changes")

    assert changes
    assert changes[0]["path"] == "goals_tree"
    assert changes[0]["before"] == before["goals_tree"]
    assert changes[0]["after"] == after["goals_tree"]


def test_contextual_resolution_does_not_corrupt_state(env, capsys):
    run(env, "add goal CtxGoal")
    run(env, "add step S1")
    run(env, "add step S2")

    before = copy.deepcopy(env["state"])
    run(env, "finish that")  # vague reference
    after = env["state"]

    # Only expected fields should change
    added, removed, changed = diff(before, after)

    assert "goals_tree" in changed
    assert "last_step_referenced" in changed
    assert len(removed) == 0


def test_semantic_resolution_does_not_corrupt_state(env, capsys):
    run(env, "add goal SemGoal")
    run(env, "add step S1")

    before = copy.deepcopy(env["state"])
    run(env, "do the next thing")  # semantic vagueness
    after = env["state"]

    added, removed, changed = diff(before, after)

    assert "goals_tree" in changed
    assert len(removed) == 0
