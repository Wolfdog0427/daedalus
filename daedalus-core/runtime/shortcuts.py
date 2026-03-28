# runtime/shortcuts.py

import copy
import re
from typing import Optional, Dict, Any


# ------------------------------------------------------------
# Normalization
# ------------------------------------------------------------

def normalize(text: str) -> str:
    """
    Lowercase, trim, and collapse whitespace.
    """
    return re.sub(r"\s+", " ", text.strip().lower())


# ------------------------------------------------------------
# Natural-language shortcut patterns
# ------------------------------------------------------------
# Each entry is:
#   (regex_pattern, static_result OR callable(match) -> result_dict)
#
# Result dict format:
#   { "intent": <intent>, "args": {...} }

SHORTCUTS: list[tuple[str, Any]] = [

    # --------------------------------------------------------
    # Quick aliases
    # --------------------------------------------------------
    (r"^ag\s+(.+)$", lambda m: {"intent": "add goal " + m.group(1).strip()}),
    (r"^as\s+(.+)$", lambda m: {"intent": "add step " + m.group(1).strip()}),

    # --------------------------------------------------------
    # Undo / Redo
    # --------------------------------------------------------
    (r"undo( that| last action| last step)?$", {"intent": "undo", "args": {}}),
    (r"go back$", {"intent": "undo", "args": {}}),

    (r"redo( that| last action)?$", {"intent": "redo", "args": {}}),

    # --------------------------------------------------------
    # Checkpoints
    # --------------------------------------------------------
    (r"save (this|here)$", {"intent": "save_checkpoint", "args": {"name": "auto"}}),
    (r"bookmark (this|here)$", {"intent": "save_checkpoint", "args": {"name": "auto"}}),

    (r"save point (.+)$",
        lambda m: {"intent": "save_checkpoint", "args": {"name": m.group(1).strip()}}),

    (r"load point (.+)$",
        lambda m: {"intent": "restore_checkpoint", "args": {"name": m.group(1).strip()}}),

    (r"restore point (.+)$",
        lambda m: {"intent": "restore_checkpoint", "args": {"name": m.group(1).strip()}}),

    # --------------------------------------------------------
    # Progress navigation
    # --------------------------------------------------------
    (r"what'?s next$", {"intent": "show_next_step", "args": {}}),
    (r"next step$", {"intent": "show_next_step", "args": {}}),

    (r"previous step$", {"intent": "show_previous_step", "args": {}}),
    (r"where was i$", {"intent": "show_context", "args": {}}),

    (r"continue$", {"intent": "continue_last_action", "args": {}}),
    (r"again$", {"intent": "repeat_last_action", "args": {}}),
]


# ------------------------------------------------------------
# Shortcut resolver
# ------------------------------------------------------------

def resolve_shortcut(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Return a structured command dict if the input matches a shortcut.
    Otherwise return None.
    """
    text = normalize(raw_text)

    for pattern, result in SHORTCUTS:
        m = re.match(pattern, text)
        if not m:
            continue

        # Callable handler
        if callable(result):
            return result(m)

        # Static mapping — return a copy to prevent caller mutations
        return copy.deepcopy(result)

    return None
