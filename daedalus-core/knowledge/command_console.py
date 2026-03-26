# knowledge/command_console.py

"""
Command Console

A REPL-style interactive console for:
- natural-language commands
- dashboard summaries
- stability checks
- autonomy adjustments
- verification
- maintenance
- diagnostics

This module NEVER bypasses the autonomy governor.
All actions flow through:
    action_router → integration_layer → autonomy_governor

This is the human-facing control surface for the system.
"""

from __future__ import annotations

import sys
from typing import Dict, Any

from knowledge.action_router import route_command
from knowledge.system_dashboard import dashboard_summary
from knowledge.stability_engine import enforce_stability
from knowledge.audit_log import log_event


BANNER = """
===========================================================
              AI SYSTEM COMMAND CONSOLE
===========================================================
Type natural language commands such as:

  Knowledge & Reasoning:
  • "verify this: <claim>"      - Verify and ingest a claim
  • "explain this: <claim>"     - Request explanation
  • "run a consistency scan"    - Check knowledge consistency
  • "evolve concepts"           - Run concept evolution

  Curiosity & Learning:
  • "run curiosity"             - Detect gaps and propose goals
  • "list goals"                - Show knowledge acquisition goals
  • "approve goal: <id>"        - Approve a proposed goal
  • "quality gate: <id>"        - Run quality check on a goal

  Meta-Cognition:
  • "run meta cycle"            - Full meta-reasoning cycle
  • "meta status"               - System health summary
  • "show dashboard"            - Dashboard overview

  LLM / Provider Management:
  • "list providers"            - Show connected LLM/AGI providers
  • "discover providers"        - Run provider discovery cycle
  • "provider notifications"    - Check provider alerts

  Pipeline Tuning:
  • "tune flow"                 - Run flow optimization
  • "flow dashboard"            - Pipeline health metrics
  • "clean up storage"          - Run storage maintenance

  Governance:
  • "open up autonomy"          - Set autonomy to open
  • "lock down to strict"       - Set autonomy to strict
  • "check stability"           - Run stability check

  • "exit"                      - Exit console

All actions are governed and logged.
===========================================================
"""


# ------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------

def _print_json(obj: Dict[str, Any]):
    import json
    print(json.dumps(obj, indent=2))


def _handle_special_commands(cmd: str) -> bool:
    """
    Returns True if the command was handled here.
    """
    c = cmd.lower().strip()

    if c in ("exit", "quit", "bye"):
        print("Exiting console.")
        sys.exit(0)

    if "dashboard" in c:
        print(dashboard_summary())
        return True

    if "stability" in c or "safe mode" in c:
        result = enforce_stability()
        print("\n=== STABILITY CHECK ===")
        _print_json(result)
        return True

    return False


# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------

def start_console():
    """
    Starts the interactive command console.
    """
    print(BANNER)

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting console.")
            break

        if not cmd:
            continue

        # Special commands (dashboard, stability, exit)
        if _handle_special_commands(cmd):
            continue

        # Commands with embedded claims
        claim = None
        if "verify" in cmd.lower() or "explain" in cmd.lower() or "reason" in cmd.lower():
            # Extract claim after colon or keyword
            if ":" in cmd:
                claim = cmd.split(":", 1)[1].strip()
            else:
                # Try last word fallback
                parts = cmd.split()
                if len(parts) > 2:
                    claim = " ".join(parts[2:]).strip()

        # Route through action router
        result = route_command(cmd, claim=claim)

        # Log the console command
        log_event("console_command", {
            "command": cmd,
            "claim": claim,
            "result": result,
        })

        # Display result
        print("\n=== RESULT ===")
        _print_json(result)
