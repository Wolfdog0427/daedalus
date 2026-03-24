# tests/test_repl_mutation_fuzzer_security.py

import pytest
import random
import string

from runtime.repl import _process_line, build_assistant
from runtime.context_resolver import ContextResolver
from runtime.contextual_resolver import ContextualResolver
from runtime.state_store import StateStore
from runtime.plan_renderer import PlanRenderer
from runtime.goal_dashboard_renderer import GoalDashboardRenderer


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


BASE_COMMANDS = [
    "add goal Build a spaceship",
    "add step Design the hull",
    "complete step 1",
    "move step 1 up",
    "switch to the next goal",
    "save checkpoint cp1",
    "restore checkpoint cp1",
]


UNICODE_NOISE = [
    "💥", "🔥", "✨", "🧪", "🧠",
    "\u200b", "\u200d", "\u2060",
]


def mutate_chars(s):
    s = list(s)
    for _ in range(random.randint(1, max(1, len(s)//4))):
        op = random.choice(["insert", "delete", "swap", "flip"])
        if op == "insert":
            pos = random.randint(0, len(s))
            s.insert(pos, random.choice(string.printable))
        elif op == "delete" and s:
            pos = random.randint(0, len(s)-1)
            del s[pos]
        elif op == "swap" and len(s) > 1:
            i, j = random.sample(range(len(s)), 2)
            s[i], s[j] = s[j], s[i]
        elif op == "flip" and s:
            pos = random.randint(0, len(s)-1)
            s[pos] = s[pos].upper() if s[pos].islower() else s[pos].lower()
    return "".join(s)


def inject_unicode_noise(s):
    chunks = list(s)
    for _ in range(random.randint(1, 5)):
        pos = random.randint(0, len(chunks))
        chunks.insert(pos, random.choice(UNICODE_NOISE))
    return "".join(chunks)


def inject_markup_shell_json(s):
    decorations = [
        " && rm -rf /",
        " | cat /etc/passwd",
        "<script>alert(1)</script>",
        '{"weird": "json", "nested": {"x": 1}}',
        "`rm -rf *`",
        "$(echo hacked)",
    ]
    return s + random.choice(decorations)


def mutate_command(base):
    cmd = base
    for mutator in [
        mutate_chars,
        inject_unicode_noise,
        inject_markup_shell_json,
    ]:
        if random.random() < 0.9:
            cmd = mutator(cmd)
    return cmd


def test_security_hardened_nlu_survives_mutation(env, capsys):
    random.seed(1337)

    run(env, "add goal SeedGoal")
    run(env, "add step SeedStep")
    capsys.readouterr()

    for _ in range(300):
        base = random.choice(BASE_COMMANDS)
        mutated = mutate_command(base)
        run(env, mutated)
        capsys.readouterr()

    history = env["store"].history
    assert len(history) >= 50

    for entry in history:
        assert "command" in entry
        assert "result" in entry
        assert "state" in entry
        assert "nlu_cmd" in entry
        assert "command_before" in entry
        assert "context_trace" in entry

    state = env["state"]
    assert "goals_tree" in state
    assert isinstance(state["goals_tree"], list)
    assert True
