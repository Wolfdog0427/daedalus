"""
Keyword libraries for the Natural Language Understanding (NLU) layer.

"add", "insert", "append" map directly to add_step in the matcher.
Ambiguous verbs ("create", "start", "begin") stay under create_goal;
the intent_classifier refines "create step X" -> add_step if needed.
"""

# ------------------------------------------------------------
# ACTION VERB FAMILIES
# ------------------------------------------------------------

COMPLETE_VERBS = [
    "complete", "finish", "wrap", "wrap up", "check", "check off",
    "mark", "mark done", "resolve", "finalize", "close", "close out",
    "end", "do",
]

DELETE_VERBS = [
    "delete", "remove", "discard", "trash", "erase", "drop",
    "eliminate", "get rid", "get rid of",
]

RENAME_VERBS = [
    "rename", "retitle", "change", "change name", "edit name",
    "update title", "modify title",
]

ADD_VERBS = [
    "add", "insert", "append", "make", "create", "start", "begin",
]

SWITCH_VERBS = [
    "switch", "go", "go to", "jump", "jump to", "focus", "focus on",
    "move to", "activate", "open",
]

MOVE_VERBS = [
    "move", "shift", "reorder", "relocate", "put", "place",
]

RESET_VERBS = [
    "reset", "clear", "wipe", "restart", "reinitialize",
]

SHOW_VERBS = [
    "show", "display", "view",
]

UNDO_VERBS = ["undo"]
REDO_VERBS = ["redo"]
SAVE_VERBS = ["save"]
RESTORE_VERBS = ["restore"]

# ------------------------------------------------------------
# OBJECT FAMILIES
# ------------------------------------------------------------

STEP_WORDS = [
    "step", "task", "item", "thing", "action", "todo",
]

GOAL_WORDS = [
    "goal", "project", "mission", "objective", "plan",
]

# ------------------------------------------------------------
# VAGUE REFERENCE PHRASES
# ------------------------------------------------------------

STEP_REFERENCE_PHRASES = [
    "it", "that", "that step", "the last one", "the previous step",
    "the last step", "the one i just did", "the one i just finished",
    "finish it", "finish that", "finish the last one",
]

GOAL_REFERENCE_PHRASES = [
    "my last goal", "the last goal", "the previous goal",
    "the one i just created",
]

# ------------------------------------------------------------
# MODIFIER CLUSTERS
# ------------------------------------------------------------

MODIFIERS = {
    "next":     ["next", "after", "following"],
    "previous": ["previous", "before", "earlier"],
    "first":    ["first", "top", "beginning"],
    "last":     ["last", "final", "end"],
}

# ------------------------------------------------------------
# INTENT CLUSTERS
# ------------------------------------------------------------

INTENT_CLUSTERS = {
    "complete_step":       COMPLETE_VERBS,
    "delete_step":         DELETE_VERBS,
    "rename_step":         RENAME_VERBS,

    "add_step":            ["add", "insert", "append"],

    "create_goal":         ["create", "start", "begin"],

    "switch_goal":         SWITCH_VERBS,
    "move_step":           MOVE_VERBS,
    "reset_state":         RESET_VERBS,
    "show_plan":           SHOW_VERBS,
    "undo":                UNDO_VERBS,
    "redo":                REDO_VERBS,
    "save_checkpoint":     SAVE_VERBS,
    "restore_checkpoint":  RESTORE_VERBS,
}

# ------------------------------------------------------------
# CANONICAL ACTION MAPPINGS
# ------------------------------------------------------------

CANONICAL_ACTIONS = {}

for intent, verbs in INTENT_CLUSTERS.items():
    for v in verbs:
        CANONICAL_ACTIONS[v] = intent
