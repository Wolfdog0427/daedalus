"""
Full End-to-End Mega Test Suite for the Assistant Cognitive Stack.

Run inside the REPL with:
    debug on
    execfile("tests/mega_suite.py")

Or paste commands manually.

This suite tests:
- NLU pipeline
- Resolver adapter
- Context resolver
- Execution engine
- Goal manager
- Step manager
- Vague references
- Multi-goal switching
- Debug instrumentation
- Logging
- Diffing
- Graphviz pipeline generation
- Step-through execution (optional)
"""

import time

def run(cmd):
    print(f"\n>>> {cmd}")
    return cmd


TEST_SEQUENCE = [

    # ------------------------------------------------------------
    # 1. Basic goal creation
    # ------------------------------------------------------------
    "create a new goal called Build a shed",
    "add a step called buy wood",
    "add a step called cut wood",
    "add a step called assemble frame",

    # ------------------------------------------------------------
    # 2. Vague references
    # ------------------------------------------------------------
    "finish it",                 # should complete "assemble frame"
    "delete the last one",       # should delete "cut wood"
    "rename it to cut lumber",   # rename last step

    # ------------------------------------------------------------
    # 3. Explicit step numbers
    # ------------------------------------------------------------
    "complete step 1",           # complete "buy wood"
    "delete step 2",             # delete "cut lumber"

    # ------------------------------------------------------------
    # 4. Create a second goal
    # ------------------------------------------------------------
    "create a new goal called Build a deck",
    "add a step called buy boards",
    "add a step called dig holes",

    # ------------------------------------------------------------
    # 5. Switch goals
    # ------------------------------------------------------------
    "switch to my last goal",    # should switch to Build a deck

    # ------------------------------------------------------------
    # 6. Vague goal reference
    # ------------------------------------------------------------
    "go to the previous goal",   # should switch back to Build a shed

    # ------------------------------------------------------------
    # 7. Reset state
    # ------------------------------------------------------------
    "reset state",

    # ------------------------------------------------------------
    # 8. Rebuild after reset
    # ------------------------------------------------------------
    "create a new goal called Learn guitar",
    "add a step called buy strings",
    "add a step called tune guitar",
    "finish the last one",

    # ------------------------------------------------------------
    # 9. Stress test vague references
    # ------------------------------------------------------------
    "finish it",
    "finish that",
    "finish the last step",
    "finish the one i just did",

    # ------------------------------------------------------------
    # 10. Stress test modifiers
    # ------------------------------------------------------------
    "add a step called practice chords",
    "add a step called practice scales",
    "complete the next step",
    "delete the previous step",

    # ------------------------------------------------------------
    # 11. Final state debug
    # ------------------------------------------------------------
    "debug_state",
    "debug_goals",
    "debug_steps",
]


def run_mega_suite():
    print("\n=== RUNNING FULL END-TO-END MEGA SUITE ===\n")
    time.sleep(0.5)

    for cmd in TEST_SEQUENCE:
        print(f"> {cmd}")
        time.sleep(0.1)  # small delay for readability
        yield cmd

    print("\n=== MEGA SUITE COMPLETE ===\n")
