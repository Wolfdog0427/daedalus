# cli/console.py

from __future__ import annotations
import argparse
import json

from api.ui_gateway import handle_request
from cli.watch import watch
from cli.governor_thresholds import render_governor_thresholds
from governor.autonomy_governor import governor


def main() -> None:
    parser = argparse.ArgumentParser(description="Assistant Core CLI")

    parser.add_argument(
        "command",
        help=(
            "Commands: status, health, run_cycle, run_scheduler, readiness, "
            "governor_trace, governor_thresholds, watch, "
            "governor_set_thresholds, governor_save_thresholds, "
            "governor_load_thresholds, governor_reset_thresholds"
        ),
    )
    parser.add_argument("--args", default="{}")
    parser.add_argument("--interval", type=float, default=2.0)

    ns = parser.parse_args()

    # ------------------------------------------------------------
    # Special CLI commands
    # ------------------------------------------------------------

    if ns.command == "watch":
        watch(ns.interval)
        return

    if ns.command == "governor_thresholds":
        print(render_governor_thresholds(governor))
        return

    # ------------------------------------------------------------
    # Parse args safely
    # ------------------------------------------------------------

    try:
        args = json.loads(ns.args)
    except json.JSONDecodeError:
        args = {}

    # ------------------------------------------------------------
    # Build request
    # ------------------------------------------------------------

    request = {"command": ns.command, "args": args}
    response = handle_request(request)

    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
