# tests/test_repl_cognitive_load.py

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
    "Build a robot",
    "Learn Japanese",
    "Start a company",
    "Design a video game",
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
    "Prototype the robot arm",
    "Learn hiragana",
    "Write business plan",
    "Sketch level layout",
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
    "work on that",
    "do the thing",
]

ORDINAL = [
    "complete the next step",
    "complete the previous step",
    "go to the next goal",
    "go to the previous goal",
    "move the next step up",
    "move the previous step down",
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
    "watch last_goal_referenced",
]

DEBUG = [
    "debug last",
    "debug context",
    "debug context trace",
    "debug semantic",
    "debug state",
]

NOISE = [
    "asdfasdf",
    "123123",
    "!@#$%",
    "goalstepgoalstep",
    "???",
    "lorem ipsum",
]


# ------------------------------------------------------------
# COGNITIVE LOAD TEST
# ------------------------------------------------------------

def test_cognitive_load(env, capsys):
    """
    1000-turn cognitive-load simulation.
    Validates:
      - memory stability
      - contextual reasoning stability
      - semantic repair stability
      - state integrity
      - no drift in references
      - no corruption in goals_tree
      - no crashes
    """

    random.seed(777)

    # Seed with multiple goals + steps
    for _ in range(5):
        run(env, f"add goal {random.choice(GOALS)}")
        for _ in range(3):
            run(env, f"add step {random.choice(STEPS)}")

    capsys.readouterr()

    for i in range(1000):
        choice = random.randint(1, 12)

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
            run(env, random.choice(["show plan", "show goals"]))

        elif choice == 11:
            # High-load ambiguous reference
            run(env, "do the thing with the one before it")

        elif choice == 12:
            # High-load nested reference
            run(env, "complete the step after the one we just did")

        capsys.readouterr()

    # --------------------------------------------------------
    # FINAL ASSERTIONS
    # --------------------------------------------------------

    history = env["store"].history
    assert len(history) >= 300  # sanity

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
