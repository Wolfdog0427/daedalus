# tests/test_repl_pipeline.py

import pytest

from runtime.repl import (
    _process_line,
    build_assistant,
)
from runtime.context_resolver import ContextResolver
from runtime.contextual_resolver import ContextualResolver
from runtime.state_store import StateStore
from runtime.plan_renderer import PlanRenderer
from runtime.goal_dashboard_renderer import GoalDashboardRenderer
from runtime.repl_context import REPLContext


# ------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------

@pytest.fixture
def repl_env():
    """
    Creates a clean REPL environment identical to run_repl(),
    but without interactive input.
    """
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


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def run_line(env, text):
    """Runs a single REPL line through _process_line."""
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
# DISPATCHER TESTS
# ------------------------------------------------------------

def test_dispatcher_goals_show(repl_env, capsys):
    run_line(repl_env, "show goals")
    out = capsys.readouterr().out
    assert "Goals" in out or "goals" in out


def test_dispatcher_system_health(repl_env, capsys):
    run_line(repl_env, "system health")
    out = capsys.readouterr().out
    assert "health" in out.lower()


# ------------------------------------------------------------
# NLU → SEMANTIC → CONTEXTUAL → STATE PIPELINE
# ------------------------------------------------------------

def test_pipeline_records_nlu_snapshot(repl_env, capsys):
    run_line(repl_env, "add goal test goal")
    entry = repl_env["store"].history[-1]
    assert "nlu_cmd" in entry
    assert isinstance(entry["nlu_cmd"], dict)


def test_pipeline_records_contextual_trace(repl_env, capsys):
    run_line(repl_env, "complete the step")
    entry = repl_env["store"].history[-1]
    assert "context_trace" in entry
    assert isinstance(entry["context_trace"], list)


def test_pipeline_records_before_after_context_resolution(repl_env, capsys):
    run_line(repl_env, "complete the step")
    entry = repl_env["store"].history[-1]
    assert "command_before" in entry
    assert isinstance(entry["command_before"], dict)


# ------------------------------------------------------------
# CONTEXTUAL RESOLUTION BEHAVIOR
# ------------------------------------------------------------

def test_contextual_resolver_uses_last_step(repl_env, capsys):
    # Create a goal + step
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "add step First step")

    # Complete step with vague reference
    run_line(repl_env, "complete the step")

    entry = repl_env["store"].history[-1]
    cmd = entry["command"]
    assert cmd["args"]["step_number"] == 1


def test_contextual_resolver_updates_last_references(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "add step Something")
    run_line(repl_env, "complete the step")

    state = repl_env["state"]
    assert state["last_step_referenced"] == 1
    assert state["last_goal_referenced"] == 1


# ------------------------------------------------------------
# DEBUG COMMANDS
# ------------------------------------------------------------

def test_debug_semantic_contextual(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "debug semantic")

    out = capsys.readouterr().out
    assert "SEMANTIC" in out.upper()
    assert "CONTEXTUAL" in out.upper()


def test_debug_last(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "debug last")

    out = capsys.readouterr().out
    assert "LAST COMMAND" in out.upper()


def test_debug_context_trace(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "complete the step")
    run_line(repl_env, "debug context trace")

    out = capsys.readouterr().out
    assert "TRACE" in out.upper()


# ------------------------------------------------------------
# SHORTCUTS
# ------------------------------------------------------------

def test_shortcut_execution(repl_env, capsys):
    # Assuming "ag" is a shortcut for "add goal"
    run_line(repl_env, "ag Test via shortcut")
    entry = repl_env["store"].history[-1]
    assert entry["command"]["intent"] == "add_goal"


# ------------------------------------------------------------
# UNDO / REDO
# ------------------------------------------------------------

def test_undo_redo(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "undo")
    out = capsys.readouterr().out
    assert "undone" in out.lower() or "undo" in out.lower()

    run_line(repl_env, "redo")
    out = capsys.readouterr().out
    assert "redo" in out.lower()


# ------------------------------------------------------------
# WATCHPOINTS
# ------------------------------------------------------------

def test_watchpoint_trigger(repl_env, capsys):
    run_line(repl_env, "watch goals_tree")
    run_line(repl_env, "add goal Test")
    entry = repl_env["store"].history[-1]
    assert entry.get("watch_changes")


# ------------------------------------------------------------
# CHECKPOINTS
# ------------------------------------------------------------

def test_checkpoint_save_restore(repl_env, capsys):
    run_line(repl_env, "add goal Test")
    run_line(repl_env, "save checkpoint cp1")
    run_line(repl_env, "add goal Another")
    run_line(repl_env, "restore checkpoint cp1")

    out = capsys.readouterr().out
    assert "restored" in out.lower() or "checkpoint" in out.lower()
