# tests/test_repl_stress.py

import pytest
import random

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
# RANDOM COMMAND POOL
# ------------------------------------------------------------

GOAL_NAMES = [
    "Build a spaceship",
    "Learn quantum physics",
    "Write a novel",
    "Master piano",
    "Train for marathon",
]

STEP_NAMES = [
    "Design the hull",
    "Study wavefunctions",
    "Draft chapter one",
    "Practice scales",
    "Run 5 miles",
    "Install the engine",
    "Solve Schrödinger equation",
    "Test flight systems",
]

VAGUE_REFS = [
    "complete the step",
    "finish that",
    "do the next thing",
    "move it up",
    "move it down",
    "switch to the next goal",
    "switch to the previous goal",
]

DASHBOARD_COMMANDS = [
    "goals sort name",
    "goals sort progress",
    "goals sort created",
    "goals filter all",
    "goals filter active",
    "goals filter completed",
]

DEBUG_COMMANDS = [
    "debug last",
    "debug context",
    "debug context trace",
    "debug semantic",
]

CHECKPOINT_COMMANDS = [
    "save checkpoint cpA",
    "save checkpoint cpB",
    "restore checkpoint cpA",
    "restore checkpoint cpB",
]

WATCHPOINT_COMMANDS = [
    "watch goals_tree",
    "watch active_goal_id",
]


# ------------------------------------------------------------
# STRESS TEST
# ------------------------------------------------------------

def test_repl_stress(env, capsys):
    """
    This test fires 300 randomized commands through the full REPL pipeline.
    It validates:
      - no crashes
      - state remains internally consistent
      - contextual resolution never raises
      - history entries always contain required fields
      - undo/redo/checkpoints/watchpoints behave under load
    """

    random.seed(1337)

    for i in range(300):
        choice = random.randint(1, 8)

        if choice == 1:
            # Add goal
            name = random.choice(GOAL_NAMES)
            run(env, f"add goal {name}")

        elif choice == 2:
            # Add step
            name = random.choice(STEP_NAMES)
            run(env, f"add step {name}")

        elif choice == 3:
            # Vague reference
            run(env, random.choice(VAGUE_REFS))

        elif choice == 4:
            # Dashboard controls
            run(env, random.choice(DASHBOARD_COMMANDS))

        elif choice == 5:
            # Debug commands
            run(env, random.choice(DEBUG_COMMANDS))
            capsys.readouterr()

        elif choice == 6:
            # Checkpoints
            run(env, random.choice(CHECKPOINT_COMMANDS))

        elif choice == 7:
            # Watchpoints
            run(env, random.choice(WATCHPOINT_COMMANDS))

        elif choice == 8:
            # Undo/redo
            run(env, random.choice(["undo", "redo"]))

        # Drain output to avoid buffer buildup
        capsys.readouterr()

    # --------------------------------------------------------
    # FINAL ASSERTIONS
    # --------------------------------------------------------

    history = env["store"].history
    assert len(history) >= 50  # sanity

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

    # No crashes, no exceptions — if we reached here, the system survived
    assert True
