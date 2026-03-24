# cli.py

"""
CLI wrapper for one-shot commands.
"""

from __future__ import annotations

import argparse
import json

from knowledge.action_router import route_command
from knowledge.system_dashboard import dashboard_summary
from knowledge.stability_engine import enforce_stability


def main():
    parser = argparse.ArgumentParser(description="Cognitive System CLI")
    parser.add_argument("command", nargs="+", help="Natural language command")
    parser.add_argument("--claim", type=str, help="Optional claim text")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard")
    parser.add_argument("--stability", action="store_true", help="Check stability")
    args = parser.parse_args()

    if args.dashboard:
        print(dashboard_summary())
        return

    if args.stability:
        print(json.dumps(enforce_stability(), indent=2))
        return

    cmd = " ".join(args.command)
    result = route_command(cmd, claim=args.claim)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
