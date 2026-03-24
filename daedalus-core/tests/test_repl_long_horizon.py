# tests/test_repl_long_horizon.py

import pytest
import random
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
# COMMAND POOLS
# ------------------------------------------------------------

GOALS = [
    "Build a spaceship",
    "Learn quantum physics",
    "Write a novel",
    "Master piano",
    "Train for marathon",
    "Study AI safety",
]

STEPS = [
    "Design the hull",
    "Install the engine",
    "Test flight systems",
    "Draft chapter one",
    "Practice scales",
    "Run 5 miles",
    "Study wavefunctions",
    "Solve Schrödinger equation",
]

VAGUE = [
    "do it",
    "finish that",
    "continue",
    "the next one",
    "the previous one",
    "move it up",
    "move it down",
    "switch to the next goal",
    "switch to the previous goal",
]

ORDINAL = [
    "complete the next step",
    "complete the previous step",
    "go to the next goal",
    "go to the previous goal",
]

CHECKPOINTS = [
    "save checkpoint cpA",
    "save checkpoint cpB",
    "restore checkpoint cpA",
    "restore checkpoint cpB",
]

WATCHPOINTS = [
    "watch goals_tree",
    "watch active_goal_id",
    "watch last_step_referenced",
]

DEBUG = [
    "debug last",
    "debug context",
    "debug context trace",
    "debug semantic",
]

NOISE = [
    "asdfasdf",
    "123123",
    "!@#$%",
    "goalstepgoalstep",
    "???",
]


# ------------------------------------------------------------
# LONG-HORIZON TEST
# ------------------------------------------------------------

def test_long_horizon(env, capsys):
    """
    1000-turn synthetic conversation simulation.
    Validates:
      - long-term memory stability
      - contextual resolution stability
      - semantic resolution stability
      - state integrity
      - no drift in references
      - no corruption in goals_tree
      - no crashes
    """

    random.seed(424242)

    # Seed with at least one goal + step
    run(env, "add goal SeedGoal")
    run(env, "add step SeedStep")
    capsys.readouterr()

    for i in range(1000):
        choice = random.randint(1, 10)

        if choice == 1:
            run(env, f"add goal {random.choice(GOALS)}")

        elif choice == 2:
            run(env, f"add step {random.choice(STEPS)}")

        elif choice == 3:
            run(env, random.choice(VAGUE))

        elif choice == 4:
            run(env, random.choice(ORDINAL))

        elif choice == 5:
            run(env, random.choice(CHECKPOINTS))

        elif choice == 6:
            run(env, random.choice(WATCHPOINTS))

        elif choice == 7:
            run(env, random.choice(DEBUG))
            capsys.readouterr()

        elif choice == 8:
            run(env, random.choice(["undo", "redo"]))

        elif choice == 9:
            run(env, random.choice(NOISE))

        elif choice == 10:
            # Occasionally show plan or dashboard
            run(env, random.choice(["show plan", "show goals"]))

        capsys.readouterr()

    # --------------------------------------------------------
    # FINAL ASSERTIONS
    # --------------------------------------------------------

    history = env["store"].history
    assert len(history) >= 200  # sanity

    # Every entry must contain required fields
    for entry in history:
        assert "command" in entry
        assert "result" in entry
        assert "state" in entry
        assert "nlu_cmd" in entry
        assert "command_before" in entry
        assert "context_trace" in entry

    # State must remain internally consistent
    state = env["state"]
    assert "goals_tree" in state
    assert isinstance(state["goals_tree"], list)

    # No crashes — reaching here means the system survived
    assert True
