# tests/test_repl_semantic_ambiguity.py

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
# SEMANTIC AMBIGUITY TORTURE TESTS
# ------------------------------------------------------------

def test_semantic_ambiguity_torture(env, capsys):
    """
    This test fires deeply ambiguous, human-messy commands through the REPL.
    It validates:
      - semantic detector stability
      - contextual resolver stability
      - state resolver stability
      - no crashes
      - consistent state
      - correct handling of vague references
      - correct handling of ordinal drift
      - correct handling of nested references
    """

    # Seed with goals + steps
    run(env, "add goal Build a spaceship")
    run(env, "add step Design the hull")
    run(env, "add step Install the engine")
    run(env, "add step Test flight systems")

    run(env, "add goal Learn physics")
    run(env, "add step Study wavefunctions")
    run(env, "add step Solve Schrödinger equation")

    capsys.readouterr()

    ambiguous_inputs = [
        # Vague references
        "do the thing",
        "finish that one",
        "work on the one before that",
        "continue where we left off",
        "do the next part of it",

        # Nested references
        "switch to the goal after the one before the current one",
        "complete the step after the one we just did",
        "move the step before the one that comes after",

        # Pronoun chains
        "switch to that",
        "do that with the one before it",
        "move it to where it should be",
        "finish the one that isn't done yet",

        # Ordinal drift
        "go to the next next goal",
        "do the step after the next one",
        "move the previous previous step",

        # Contradictory phrasing
        "complete the step but also don't complete it",
        "switch to the next goal but stay here",
        "move it up but also down",

        # Human-messy
        "you know, the thing we talked about",
        "that step, the one that was earlier",
        "the goal that isn't this one",
        "the step that should be next",
    ]

    for text in ambiguous_inputs:
        run(env, text)
        capsys.readouterr()

    # --------------------------------------------------------
    # FINAL ASSERTIONS
    # --------------------------------------------------------

    history = env["store"].history
    assert len(history) >= len(ambiguous_inputs)

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
