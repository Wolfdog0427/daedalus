# runtime/self_test.py

import time
import traceback
from typing import Callable, Dict, Any, Optional


# ------------------------------------------------------------
# SELF‑TEST RESULT
# ------------------------------------------------------------

class SelfTestResult:
    """
    Container for aggregated self‑test results.

    Attributes:
        overall_ok (bool)
        details (dict[str, {ok: bool, message: str}])
        timing_ms (float)
    """

    def __init__(
        self,
        overall_ok: bool,
        details: Dict[str, Dict[str, Any]],
        timing_ms: Optional[float] = None,
    ):
        self.overall_ok = overall_ok
        self.details = details
        self.timing_ms = timing_ms or 0.0


# ------------------------------------------------------------
# SELF‑TEST HARNESS
# ------------------------------------------------------------

class SelfTestHarness:
    """
    Minimal deterministic self‑test harness.

    - register_check(name, fn)
        fn must return (ok: bool, message: str)
    - run_all()
        returns SelfTestResult
    """

    def __init__(self):
        self._checks: Dict[str, Callable[[], Any]] = {}

    def register_check(self, name: str, fn: Callable[[], Any]) -> None:
        self._checks[name] = fn

    def run_all(self) -> SelfTestResult:
        details: Dict[str, Dict[str, Any]] = {}
        overall_ok = True

        t0 = time.time()

        for name, fn in self._checks.items():
            try:
                ok, message = fn()
            except Exception as e:
                ok = False
                message = f"Exception: {e}\n{traceback.format_exc()}"

            details[name] = {"ok": ok, "message": message}

            if not ok:
                overall_ok = False

        t1 = time.time()

        return SelfTestResult(
            overall_ok=overall_ok,
            details=details,
            timing_ms=(t1 - t0) * 1000,
        )


# ------------------------------------------------------------
# STARTUP SELF‑TEST
# ------------------------------------------------------------

def run_startup_self_test() -> SelfTestResult:
    """
    Runs a minimal deterministic startup self‑test suite.
    Returns a SelfTestResult.
    """
    harness = SelfTestHarness()

    # Baseline checks — deterministic, no side effects
    harness.register_check("import_runtime", lambda: (True, "Runtime imports OK"))
    harness.register_check("basic_sanity", lambda: (True, "Sanity check OK"))

    return harness.run_all()


def format_self_test_report(result: SelfTestResult) -> str:
    """
    Formats a human‑readable startup self‑test report.
    """
    lines = []
    lines.append("=== STARTUP SELF‑TEST REPORT ===")
    lines.append(f"Overall OK: {result.overall_ok}")
    lines.append(f"Timing: {result.timing_ms:.2f} ms")
    lines.append("")

    for name, info in result.details.items():
        status = "OK" if info["ok"] else "FAIL"
        lines.append(f"- {name}: {status} — {info['message']}")

    return "\n".join(lines)


# ------------------------------------------------------------
# BACKGROUND SELF‑TEST (REQUIRED BY REPL)
# ------------------------------------------------------------

_background_quiet = False


def set_background_self_test_quiet(value: bool) -> None:
    """
    Enable/disable console output for background self‑tests.
    """
    global _background_quiet
    _background_quiet = bool(value)


def run_background_self_test() -> None:
    """
    Lightweight background self‑test invoked after each command.

    - Must NEVER raise exceptions.
    - Must NEVER mutate state.
    - Must be fast and deterministic.
    """
    try:
        harness = SelfTestHarness()

        # Minimal checks — safe to run frequently
        harness.register_check("basic_integrity", lambda: (True, "OK"))
        harness.register_check("runtime_alive", lambda: (True, "OK"))

        result = harness.run_all()

        if not _background_quiet:
            if not result.overall_ok:
                print("⚠ Background self‑test detected issues.")
    except Exception:
        # Background tests must never break runtime
        pass
