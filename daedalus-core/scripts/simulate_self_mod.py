# scripts/simulate_self_mod.py

"""
Self-Healing System Test Harness

This script exercises the full self-mod pipeline:
- Creates a dummy file
- Generates a fake proposal with a real edit action
- Runs an SHO cycle
- Shows sandbox + live patch results
- Prints notifications, logs, and system health

Run with:
    python scripts/simulate_self_mod.py
"""

from __future__ import annotations

import os
import json
from pprint import pprint

from api.ui_contract import get_contract
from runtime.logging_manager import tail
from runtime.notification_center import list_unread


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

DUMMY_FILE = "test_module.py"


def ensure_dummy_file():
    """Create a simple file that the SHO will modify."""
    if not os.path.exists(DUMMY_FILE):
        with open(DUMMY_FILE, "w", encoding="utf-8") as f:
            f.write('VALUE = "OLD"\n')
    print(f"[OK] Dummy file ensured: {DUMMY_FILE}")


def read_dummy_file():
    with open(DUMMY_FILE, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------
# Fake diagnostics to force a proposal
# ---------------------------------------------------------

def fake_diagnostics():
    return {
        "overall_score": 0.6,
        "overall_risk": "medium",
        "subsystems": [
            {
                "subsystem": "test_module",
                "score": 0.5,
                "risk": "medium",
            }
        ],
    }


def fake_drift():
    return {"level": "medium", "score": 0.4}


def fake_stability():
    return {"score": 0.7, "risk": "low"}


# ---------------------------------------------------------
# Inject a planned action directly into the Governor state
# ---------------------------------------------------------

def inject_planned_action():
    """
    We directly modify the pending proposal after SHO/Governor creates it.
    This is the simplest way to test the full pipeline end-to-end.
    """
    from governor.state_store import load_state, save_state

    state = load_state()
    proposals = state.get("proposals", {}).get("pending", [])

    if not proposals:
        print("[ERROR] No pending proposals found to inject actions into.")
        return None

    proposal = proposals[-1]  # last created
    proposal_id = proposal["id"]

    proposal["planned_actions"] = [
        {
            "type": "edit_file",
            "path": DUMMY_FILE,
            "transform": {
                "kind": "replace_snippet",
                "old": "OLD",
                "new": "NEW",
            },
        }
    ]

    save_state(state)
    print(f"[OK] Injected planned action into proposal {proposal_id}")
    return proposal_id


# ---------------------------------------------------------
# Main test
# ---------------------------------------------------------

def main():
    from runtime.system_console import health as get_system_health, run_cycle
    from governance.proposal_engine import approve_proposal

    print("\n=== STEP 1: Ensure dummy file exists ===")
    ensure_dummy_file()
    print("Before patch:\n", read_dummy_file())

    print("\n=== STEP 2: Run SHO cycle to generate proposal ===")
    result = run_cycle()
    pprint(result)

    print("\n=== STEP 3: Inject planned action into proposal ===")
    injected_id = inject_planned_action()
    if not injected_id:
        print("[ERROR] No proposal to inject into.")
        return

    print("\n=== STEP 4: Approve proposal ===")
    approve_proposal(injected_id)

    print("\n=== STEP 5: Run another cycle after approval ===")
    resume_result = run_cycle()
    pprint(resume_result)

    print("\n=== STEP 6: Show file after patch ===")
    print("After patch:\n", read_dummy_file())

    print("\n=== STEP 7: Unread notifications ===")
    pprint(list_unread())

    print("\n=== STEP 8: Last 20 logs ===")
    pprint(tail(20))

    print("\n=== STEP 9: Final system health ===")
    pprint(get_system_health())


if __name__ == "__main__":
    main()
