# tests/test_repl_memory_consistency.py

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
# MEMORY CONSISTENCY TESTS
# ------------------------------------------------------------

def test_last_goal_referenced_updates_correctly(env, capsys):
    run(env, "add goal Alpha")
    run(env, "add goal Beta")
    run(env, "switch to the next goal")

    state = env["state"]
    assert state["last_goal_referenced"] == state["active_goal_id"]


def test_last_step_referenced_updates_on_step_ops(env, capsys):
    run(env, "add goal StepsGoal")
    run(env, "add step One")
    run(env, "add step Two")
    run(env, "complete the step")  # vague reference → step 2

    state = env["state"]
    assert state["last_step_referenced"] == 2


def test_vague_reference_uses_memory(env, capsys):
    run(env, "add goal VRGoal")
    run(env, "add step A")
    run(env, "add step B")
    run(env, "complete step 1")

    # Now vague reference should target step 1
    run(env, "complete the step")

    entry = env["store"].history[-1]["command"]
    assert entry["args"]["step_number"] == 1


def test_ordinal_reference_updates_memory(env, capsys):
    run(env, "add goal OrdGoal")
    run(env, "add step A")
    run(env, "add step B")

    run(env, "complete step 1")
    run(env, "complete the next step")

    state = env["state"]
    assert state["last_step_referenced"] == 2


def test_memory_survives_undo(env, capsys):
    run(env, "add goal UndoGoal")
    run(env, "add step X")
    run(env, "complete step 1")

    before = copy.deepcopy(env["state"])
    run(env, "undo")
    run(env, "redo")
    after = env["state"]

    assert before == after


def test_memory_survives_checkpoint_restore(env, capsys):
    run(env, "add goal CPGoal")
    run(env, "add step S1")
    run(env, "complete step 1")

    run(env, "save checkpoint cp1")

    run(env, "add step S2")
    run(env, "complete step 2")

    run(env, "restore checkpoint cp1")

    state = env["state"]
    assert state["last_step_referenced"] == 1
    assert len(state["goals_tree"][0]["steps"]) == 1


def test_memory_not_corrupted_by_ambiguous_commands(env, capsys):
    run(env, "add goal AmbGoal")
    run(env, "add step A")
    run(env, "add step B")
    run(env, "complete step 2")

    before = copy.deepcopy(env["state"])
    run(env, "do it")  # ambiguous
    after = env["state"]

    # Memory should not be corrupted
    assert after["last_step_referenced"] in (1, 2)
    assert after["last_goal_referenced"] == before["last_goal_referenced"]


def test_memory_consistency_across_goal_switching(env, capsys):
    run(env, "add goal G1")
    run(env, "add step A1")
    run(env, "add goal G2")
    run(env, "add step B1")

    run(env, "switch to the previous goal")
    state = env["state"]

    assert state["active_goal_id"] == 1
    assert state["last_goal_referenced"] == 1


def test_memory_consistency_after_contextual_resolution(env, capsys):
    run(env, "add goal CtxGoal")
    run(env, "add step S1")
    run(env, "add step S2")

    run(env, "finish that")  # vague → step 2

    state = env["state"]
    assert state["last_step_referenced"] == 2


def test_memory_consistency_after_semantic_resolution(env, capsys):
    run(env, "add goal SemGoal")
    run(env, "add step S1")

    run(env, "do the next thing")  # semantic vagueness

    state = env["state"]
    assert state["last_step_referenced"] in (1, None)
