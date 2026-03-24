# tests/test_repl_fuzzy_adversarial.py

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
# ADVERSARIAL INPUT POOLS
# ------------------------------------------------------------

TYPO_GOAL = [
    "ad goll build a ship",
    "add gaoal lern physix",
    "ag buid a spaship",
    "adde gole writ a novl",
]

TYPO_STEP = [
    "ad stp desin hul",
    "add stepp instal engin",
    "ad steb test flite sistems",
]

AMBIGUOUS = [
    "do it",
    "finish that",
    "continue",
    "the next one",
    "the previous one",
    "move it",
    "switch it",
]

HOMOPHONES = [
    "add gole",
    "add coal",
    "add goalz",
    "complete the stepp",
    "move the stair",
]

COLLISIONS = [
    "add and delete the step",
    "complete and move the step",
    "switch and rename the goal",
]

VAGUE_ORDINALS = [
    "go to the next",
    "switch to the one after",
    "move to the one before",
]

GARBAGE = [
    "asdfasdf",
    "123123",
    "!@#$%",
    "goalstepgoalstep",
]

RANDOM_NOISE = [
    "add goal ???",
    "complete step ???",
    "move step ???",
    "switch goal ???",
]


# ------------------------------------------------------------
# STRESS TEST
# ------------------------------------------------------------

def test_fuzzy_repair_adversarial(env, capsys):
    """
    This test fires 200 adversarial fuzzy-repair inputs through the REPL.
    It validates:
      - fuzzy repair never crashes
      - contextual resolver never crashes
      - state resolver never crashes
      - execution engine never crashes
      - history entries remain valid
      - system remains internally consistent
    """

    random.seed(999)

    # Seed the system with at least one goal + step
    run(env, "add goal SeedGoal")
    run(env, "add step SeedStep")

    pools = [
        TYPO_GOAL,
        TYPO_STEP,
        AMBIGUOUS,
        HOMOPHONES,
        COLLISIONS,
        VAGUE_ORDINALS,
        GARBAGE,
        RANDOM_NOISE,
    ]

    for _ in range(200):
        pool = random.choice(pools)
        text = random.choice(pool)
        run(env, text)
        capsys.readouterr()

    # --------------------------------------------------------
    # FINAL ASSERTIONS
    # --------------------------------------------------------

    history = env["store"].history
    assert len(history) > 20  # sanity

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
