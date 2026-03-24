# runtime/watch_monitor.py

"""
Watch monitor — Option A (real alerts only)

Fix:
- Strip ANSI escape codes before evaluating messages.
"""

import re
from typing import List

from runtime.health_dashboard import update_last_watch_anomalies
from runtime.debug_tools import debug_watch_alerts
from runtime.state_store import StateStore
from runtime.self_test import run_startup_self_test, format_self_test_report
from runtime.system_doctor import run_system_doctor


# Correct ANSI escape stripping regex
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

NO_ALERT_STRINGS = {
    "",
    "(no alerts)",
    "No watchpoints triggered.",
    "(no watchpoints)",
}


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes."""
    return ANSI_ESCAPE.sub("", text or "").strip()


def _is_real_alert(msg: str) -> bool:
    """
    Determine whether the debug_watch_alerts() output represents
    a *real* watchpoint violation.
    """
    if not msg:
        return False

    clean = strip_ansi(msg)

    if clean in NO_ALERT_STRINGS:
        return False

    if clean.lower().startswith("no watchpoints"):
        return False

    if all(not line.strip() for line in clean.splitlines()):
        return False

    return True


def analyze_last_action_for_watch_anomalies(auto_repair: bool = True) -> None:
    store = StateStore()

    if not store.history:
        return

    last = store.history[-1]
    msg = debug_watch_alerts(last)

    if not _is_real_alert(msg):
        return

    clean = strip_ansi(msg)
    lines: List[str] = []

    print("[watch-monitor] Watchpoint violation detected:")
    for line in clean.splitlines():
        if line.strip():
            print(f"[watch-monitor] {line}")
            lines.append(line)

    update_last_watch_anomalies(lines)

    if auto_repair:
        print("[watch-monitor] Running self-test due to watchpoint violation...")
        report = run_startup_self_test()
        print("[watch-monitor] Self-test after watchpoint violation:")
        print(format_self_test_report(report))

        if report["status"] in ("degraded", "fail"):
            print("[watch-monitor] Running system doctor due to degraded/fail status...")
            run_system_doctor(auto=True)
