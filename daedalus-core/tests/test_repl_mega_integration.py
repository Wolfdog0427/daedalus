# tests/test_repl_mega_integration.py

import pytest

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
    pm, ds, df = _process_line(
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
    env["plan_mode"] = pm
    env["dashboard_sort"] = ds
    env["dashboard_filter"] = df
    return pm, ds, df


# ------------------------------------------------------------
# MEGA INTEGRATION TEST
# ------------------------------------------------------------

def test_full_system_integration(env, capsys):
    """
    This test simulates a real user session with:
      - multiple goals
      - multiple steps
      - vague references
      - ordinal references
      - movement
      - checkpoints
      - undo/redo
      - watchpoints
      - debug commands
      - dashboard controls
      - plan rendering
      - contextual + state resolution
    """

    # --------------------------------------------------------
    # 1. Create two goals
    # --------------------------------------------------------
    run(env, "add goal Build a spaceship")
    run(env, "add goal Learn quantum physics")

    assert len(env["state"]["goals_tree"]) == 2

    # --------------------------------------------------------
    # 2. Add steps to goal 1 (switch back since goal 2 is now active)
    # --------------------------------------------------------
    run(env, "switch to goal 1")
    run(env, "add step Design the hull")
    run(env, "add step Install the engine")
    run(env, "add step Test flight systems")

    assert len(env["state"]["goals_tree"][0]["steps"]) == 3

    # --------------------------------------------------------
    # 3. Vague reference: "complete the step"
    # Should complete last referenced step
    # --------------------------------------------------------
    run(env, "complete the step")
    last = env["store"].history[-1]["command"]
    assert last["intent"] == "complete_step"
    assert last["args"]["step_number"] == 3

    # --------------------------------------------------------
    # 4. Ordinal reference: "next goal"
    # --------------------------------------------------------
    run(env, "switch to the next goal")
    assert env["state"]["active_goal_id"] == 2

    # --------------------------------------------------------
    # 5. Add steps to second goal
    # --------------------------------------------------------
    run(env, "add step Study wavefunctions")
    run(env, "add step Solve Schrödinger equation")

    assert len(env["state"]["goals_tree"][1]["steps"]) == 2

    # --------------------------------------------------------
    # 6. Movement: "move it up"
    # --------------------------------------------------------
    run(env, "move it up")
    cmd = env["store"].history[-1]["command"]
    assert cmd["intent"] == "move_step"
    assert cmd["args"]["movement"] == -1

    # --------------------------------------------------------
    # 7. Watchpoints
    # --------------------------------------------------------
    run(env, "watch goals_tree")
    run(env, "add step Quantum entanglement")

    entry = env["store"].history[-1]
    assert entry.get("watch_changes")

    # --------------------------------------------------------
    # 8. Checkpoints
    # --------------------------------------------------------
    run(env, "save checkpoint cp1")
    run(env, "add goal Temporary goal")
    run(env, "restore checkpoint cp1")

    assert len(env["state"]["goals_tree"]) == 2  # restored

    # --------------------------------------------------------
    # 9. Undo / redo
    # --------------------------------------------------------
    run(env, "add goal UndoTest")
    run(env, "undo")
    assert len(env["state"]["goals_tree"]) == 2

    run(env, "redo")
    assert len(env["state"]["goals_tree"]) == 3

    # --------------------------------------------------------
    # 10. Dashboard controls
    # --------------------------------------------------------
    run(env, "goals sort name")
    assert env["dashboard_sort"] == "name"

    run(env, "goals filter active")
    assert env["dashboard_filter"] == "active"

    # --------------------------------------------------------
    # 11. Debug commands
    # --------------------------------------------------------
    run(env, "debug semantic")
    out = capsys.readouterr().out
    assert "SEMANTIC" in out.upper()
    assert "CONTEXTUAL" in out.upper()

    run(env, "debug context trace")
    out = capsys.readouterr().out
    assert "TRACE" in out.upper()

    run(env, "debug last")
    out = capsys.readouterr().out
    assert "LAST COMMAND" in out.upper()

    # --------------------------------------------------------
    # 12. Plan rendering
    # --------------------------------------------------------
    run(env, "show plan")
    out = capsys.readouterr().out
    assert "Step" in out or "step" in out

    # --------------------------------------------------------
    # 13. System health + doctor
    # --------------------------------------------------------
    run(env, "system health")
    out = capsys.readouterr().out
    assert "health" in out.lower()

    run(env, "run doctor")
    out = capsys.readouterr().out
    assert "doctor" in out.lower()

    # --------------------------------------------------------
    # 14. Final assertion: history is populated and consistent
    # --------------------------------------------------------
    assert len(env["store"].history) > 10
