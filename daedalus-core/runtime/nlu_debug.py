# runtime/nlu_debug.py

import time
import json
import datetime
from typing import Dict, Any

from nlu.matcher import match_nlu
from nlu.normalizer import normalize_nlu
from nlu.intent_classifier import classify_intent
from nlu.resolver_adapter import adapt_to_command
from runtime.context_resolver import ContextResolver

LOG_PATH = "nlu_debug.log"
GRAPHVIZ_DOT_PATH = "nlu_pipeline.dot"


# ------------------------------------------------------------
# ANSI COLORS
# ------------------------------------------------------------
C = {
    "header": "\033[95m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "end": "\033[0m",
}


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# FILE LOGGER + TIMESTAMPED HISTORY
# ------------------------------------------------------------

def _timestamp() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _log_debug(entry: Dict[str, Any]) -> None:
    entry_with_ts = {"timestamp": _timestamp(), **entry}
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_with_ts, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Logging must never break runtime


# ------------------------------------------------------------
# SIDE-BY-SIDE DIFF HELPERS
# ------------------------------------------------------------

def _side_by_side(label_left: str, left: str, label_right: str, right: str) -> str:
    left_lines = left.splitlines() or [""]
    right_lines = right.splitlines() or [""]

    width_left = max(len(label_left), max(len(l) for l in left_lines))
    width_right = max(len(label_right), max(len(r) for r in right_lines))

    header = f"{label_left.ljust(width_left)} | {label_right.ljust(width_right)}"
    sep = "-" * width_left + "-+-" + "-" * width_right

    rows = [header, sep]
    max_len = max(len(left_lines), len(right_lines))
    for i in range(max_len):
        l = left_lines[i] if i < len(left_lines) else ""
        r = right_lines[i] if i < len(right_lines) else ""
        rows.append(f"{l.ljust(width_left)} | {r.ljust(width_right)}")

    return "\n".join(rows)


# ------------------------------------------------------------
# GRAPHVIZ PIPELINE VISUALIZER
# ------------------------------------------------------------

def _write_graphviz_pipeline() -> None:
    """
    Writes a DOT file describing the NLU pipeline.
    """
    dot = """digraph NLU_Pipeline {
  rankdir=LR;
  node [shape=box, style=filled, color=lightgray];

  raw_text        [label="Raw Text"];
  matcher         [label="Matcher (tokenize + fuzzy repair)"];
  normalizer      [label="Normalizer (multi-word verbs + vague refs)"];
  classifier      [label="Intent Classifier"];
  adapter         [label="Resolver Adapter"];
  resolver        [label="Context Resolver"];
  engine          [label="Execution Engine"];

  raw_text -> matcher -> normalizer -> classifier -> adapter -> resolver -> engine;
}
"""
    try:
        with open(GRAPHVIZ_DOT_PATH, "w", encoding="utf-8") as f:
            f.write(dot)
    except Exception:
        pass


# ------------------------------------------------------------
# FULL NLU DEBUG PIPELINE
# ------------------------------------------------------------

def debug_nlu_pipeline(text: str, state: Dict[str, Any]):
    resolver = ContextResolver()

    print(f"\n{C['header']}{C['bold']}--- NLU DEBUG PIPELINE ---{C['end']}")

    # 1. Matcher
    t0 = time.time()
    m = match_nlu(text)
    t1 = time.time()
    print(f"\n{C['blue']}[1] MATCHER OUTPUT ({(t1 - t0)*1000:.2f} ms){C['end']}")
    print(_pretty(m))

    # 2. Normalizer
    n = normalize_nlu(m)
    t2 = time.time()
    print(f"\n{C['cyan']}[2] NORMALIZER OUTPUT ({(t2 - t1)*1000:.2f} ms){C['end']}")
    print(_pretty(n))

    # 3. Intent Classifier
    c = classify_intent(text)
    t3 = time.time()
    print(f"\n{C['yellow']}[3] INTENT CLASSIFIER OUTPUT ({(t3 - t2)*1000:.2f} ms){C['end']}")
    print(_pretty(c))

    # 4. Resolver Adapter
    a = adapt_to_command(text, state)
    t4 = time.time()
    print(f"\n{C['green']}[4] RESOLVER ADAPTER OUTPUT ({(t4 - t3)*1000:.2f} ms){C['end']}")
    print(_pretty(a))

    # 5. Context Resolver
    r = resolver.resolve(a, state)
    t5 = time.time()
    print(f"\n{C['red']}[5] CONTEXT RESOLVER OUTPUT ({(t5 - t4)*1000:.2f} ms){C['end']}")
    print(_pretty(r))

    # Side-by-side diffs
    print(f"\n{C['bold']}[DIFF] Raw vs Repaired vs Normalized{C['end']}")
    print(
        _side_by_side(
            "RAW",
            text,
            "REPAIRED",
            m.get("repaired", text),
        )
    )
    print()
    print(
        _side_by_side(
            "REPAIRED",
            m.get("repaired", text),
            "NORMALIZED",
            n.get("normalized_text", ""),
        )
    )

    print(f"\n{C['bold']}[DIFF] Adapter vs Resolver Command{C['end']}")
    print(
        _side_by_side(
            "ADAPTER",
            _pretty(a),
            "RESOLVER",
            _pretty(r),
        )
    )

    # Log everything
    _log_debug(
        {
            "input": text,
            "matcher": m,
            "normalizer": n,
            "classifier": c,
            "adapter": a,
            "resolver": r,
            "timing_ms": {
                "matcher": (t1 - t0) * 1000,
                "normalizer": (t2 - t1) * 1000,
                "classifier": (t3 - t2) * 1000,
                "adapter": (t4 - t3) * 1000,
                "resolver": (t5 - t4) * 1000,
            },
        }
    )

    _write_graphviz_pipeline()

    print(f"\n{C['header']}{C['bold']}--- END NLU DEBUG ---{C['end']}\n")


# ------------------------------------------------------------
# STEP-THROUGH DEBUGGER FOR EXECUTION ENGINE
# ------------------------------------------------------------

def debug_execution_step(cmd: Dict[str, Any], state: Dict[str, Any], execution, goal_manager):
    """
    Step-through wrapper around execution.execute().
    Shows command + state snapshot before and after, and waits for user input.
    """
    print(f"{C['header']}{C['bold']}--- EXECUTION STEP DEBUG ---{C['end']}")
    print(f"{C['blue']}[COMMAND]{C['end']}")
    print(_pretty(cmd))

    print(f"\n{C['cyan']}[STATE BEFORE]{C['end']}")
    print(_pretty(state))

    input(f"\n{C['bold']}Press Enter to execute this command...{C['end']}")

    t0 = time.time()
    result = execution.execute(cmd, state)
    t1 = time.time()

    print(f"\n{C['green']}[RESULT] ({(t1 - t0)*1000:.2f} ms){C['end']}")
    print(result)

    print(f"\n{C['yellow']}[STATE AFTER]{C['end']}")
    print(_pretty(state))

    print(f"\n{C['header']}{C['bold']}--- END EXECUTION STEP DEBUG ---{C['end']}\n")

    _log_debug(
        {
            "type": "execution_step",
            "command": cmd,
            "result": result,
            "state_after": state,
            "timing_ms": (t1 - t0) * 1000,
        }
    )

    return result
