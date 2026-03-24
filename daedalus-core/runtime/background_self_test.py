# runtime/background_self_test.py

"""
Background self-test
Runs a lightweight self-test every command.
Verbose on non-OK unless quiet mode is enabled.
"""

from runtime.self_test import run_startup_self_test, format_self_test_report
from runtime.health_dashboard import update_last_self_test
from runtime.system_doctor import run_system_doctor

_background_quiet = False


def set_background_self_test_quiet(enabled: bool) -> None:
    global _background_quiet
    _background_quiet = enabled
    state = "ON" if enabled else "OFF"
    print(f"[background-self-test] Quiet mode {state}.")


def run_background_self_test() -> None:
    report = run_startup_self_test()
    update_last_self_test(report)

    # SelfTestResult has:
    #   - overall_ok: bool
    #   - details: dict
    if report.overall_ok:
        if not _background_quiet:
            print("[background-self-test] OK.")
        return

    # Non-OK
    if not _background_quiet:
        print("[background-self-test] Non-OK status detected:")
        print(format_self_test_report(report))

    # Determine degraded/fail by inspecting details
    degraded_or_fail = any(not d.get("ok", False) for d in report.details.values())

    if degraded_or_fail:
        print("[background-self-test] Running system doctor due to degraded/fail status...")
        run_system_doctor(auto=True)
