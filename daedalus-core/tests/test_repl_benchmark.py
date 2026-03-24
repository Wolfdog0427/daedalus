# tests/test_repl_benchmark.py

import pytest
import statistics
import time

from runtime.repl import _process_line, build_assistant
from runtime.context_resolver import ContextResolver
from runtime.contextual_resolver import ContextualResolver
from runtime.state_store import StateStore
from runtime.plan_renderer import PlanRenderer
from runtime.goal_dashboard_renderer import GoalDashboardRenderer
from nlu.resolver_adapter import adapt_to_command


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
# BENCHMARK HELPERS
# ------------------------------------------------------------

def measure(fn, *args, repeats=20):
    """Measure execution time of a function over N repeats."""
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        t1 = time.perf_counter()
        samples.append((t1 - t0) * 1000)  # ms
    return samples


def summarize(samples):
    """Return summary statistics for a list of timings."""
    return {
        "mean": statistics.mean(samples),
        "median": statistics.median(samples),
        "p95": statistics.quantiles(samples, n=100)[94],
        "p99": statistics.quantiles(samples, n=100)[98],
        "min": min(samples),
        "max": max(samples),
    }


# ------------------------------------------------------------
# BENCHMARK TESTS
# ------------------------------------------------------------

def test_benchmark_nlu(env):
    """Benchmark NLU alone."""
    samples = measure(adapt_to_command, "add goal BenchmarkGoal", env["state"])
    stats = summarize(samples)

    print("\nNLU Benchmark:", stats)

    # sanity: NLU should be fast
    assert stats["mean"] < 50  # ms


def test_benchmark_semantic_resolver(env):
    """Benchmark semantic contextual resolver."""
    cmd = adapt_to_command("complete the step", env["state"])

    samples = measure(env["contextual_resolver"].resolve, cmd, env["state"])
    stats = summarize(samples)

    print("\nSemantic Resolver Benchmark:", stats)

    assert stats["mean"] < 50


def test_benchmark_context_resolver(env):
    """Benchmark state-based context resolver."""
    cmd = adapt_to_command("complete the step", env["state"])
    cmd = env["contextual_resolver"].resolve(cmd, env["state"])

    samples = measure(env["context_resolver"].resolve, cmd, env["state"])
    stats = summarize(samples)

    print("\nContext Resolver Benchmark:", stats)

    assert stats["mean"] < 50


def test_benchmark_execution(env):
    """Benchmark execution engine."""
    run(env, "add goal BenchmarkGoal")
    cmd = adapt_to_command("add step BenchmarkStep", env["state"])
    cmd = env["contextual_resolver"].resolve(cmd, env["state"])
    cmd = env["context_resolver"].resolve(cmd, env["state"])

    samples = measure(env["execution"].execute, cmd, env["state"])
    stats = summarize(samples)

    print("\nExecution Benchmark:", stats)

    assert stats["mean"] < 50


def test_benchmark_full_pipeline(env, capsys):
    """Benchmark full REPL round-trip."""
    samples = measure(run, env, "add goal FullPipelineGoal")
    stats = summarize(samples)

    print("\nFull Pipeline Benchmark:", stats)
    capsys.readouterr()

    # Full pipeline should still be reasonably fast
    assert stats["mean"] < 120
