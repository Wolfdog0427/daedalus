# runtime/command_router.py

import re
from typing import Dict, Any, Optional, Callable


# ============================================================
# 1. COMMAND REGISTRY (REQUIRED BY REPL 3.0)
# ============================================================

COMMAND_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_command(
    canonical_intent: str,
    aliases: Optional[list[str]] = None,
    nl_patterns: Optional[list[str]] = None,
):
    """
    Decorator to register structured commands.
    REPL 3.0 expects this to exist.
    """
    def decorator(fn):
        COMMAND_REGISTRY[canonical_intent] = {
            "handler": fn,
            "aliases": aliases or [],
            "nl_patterns": nl_patterns or [],
        }
        return fn
    return decorator


def dispatch_command(text: str) -> Optional[str]:
    """
    Check if the text matches any registered structured command.
    """
    lower = text.lower().strip()

    for intent, info in COMMAND_REGISTRY.items():
        # Aliases
        for a in info.get("aliases", []):
            if lower == a:
                return intent

        # Natural-language patterns
        for p in info.get("nl_patterns", []):
            if re.match(p, lower):
                return intent

    return None


# ============================================================
# 2. LEGACY ALIASES
# ============================================================

ALIASES: Dict[str, str] = {
    "rs": "reset state",
    "sp": "show plan",
    "sg": "show goals",
    "as": "add step",
    "cs": "complete step",
}


def normalize(text: str) -> str:
    text = text.strip().lower()
    return re.sub(r"\s+", " ", text)


def expand_aliases(text: str) -> str:
    parts = text.split(" ", 1)
    head = parts[0]

    if head in ALIASES:
        mapped = ALIASES[head]
        if len(parts) == 1:
            return mapped
        return mapped + " " + parts[1]

    return text


# ============================================================
# 3. LEGACY INTENT PATTERNS (YOUR ORIGINAL SYSTEM)
# ============================================================

INTENT_PATTERNS: Dict[str, Dict[str, Any]] = {
    "reset_state": {
        "patterns": [
            r"reset( everything| all)?$",
            r"reset state$",
            r"start over$",
            r"clear( everything| all)?$",
        ],
        "description": "Reset all goals, steps, and state.",
    },
    "show_plan": {
        "patterns": [
            r"show( me)?( the)? plan$",
            r"what'?s left$",
            r"what do i have left$",
            r"show steps$",
        ],
        "description": "Show the current plan for the active goal.",
    },
    "show_goals": {
        "patterns": [
            r"show( me)?( the)? goals$",
            r"what are my goals$",
            r"list goals$",
        ],
        "description": "Show all goals.",
    },
    "add_step": {
        "patterns": [
            r"add( a)? step( to)? (.+)$",
            r"create( a)? step( called)? (.+)$",
        ],
        "description": "Add a step to the active goal.",
    },
    "complete_step": {
        "patterns": [
            r"(finish|complete|do|check off|mark) step (\d+)$",
            r"mark step (\d+) as done$",
            r"i finished step (\d+)$",
            r"(finish|complete|do|check off|mark) (it|that|the last one)$",
            r"(finish|complete|do|check off|mark)$",
        ],
        "description": "Mark a step as complete.",
    },
    "create_goal": {
        "patterns": [
            r"(create|start|make)( a)?( new)? goal( called)? (.+)$",
            r"new goal (.+)$",
        ],
        "description": "Create a new goal.",
    },
    "switch_goal": {
        "patterns": [
            r"(switch|change) to goal (\d+)$",
            r"activate goal (\d+)$",
            r"switch to my last goal$",
            r"switch to the last goal$",
            r"switch to the previous goal$",
        ],
        "description": "Switch active goal.",
    },
    "delete_step": {
        "patterns": [
            r"(delete|remove) step (\d+)$",
            r"(delete|remove) (it|that|the last one)$",
        ],
        "description": "Delete a step from the active goal.",
    },
    "rename_step": {
        "patterns": [
            r"rename step (\d+) to (.+)$",
            r"change step (\d+) to (.+)$",
            r"rename (it|that|the last one) to (.+)$",
            r"change (it|that|the last one) to (.+)$",
        ],
        "description": "Rename a step.",
    },

    # ========================================================
    # NEW: VPN INTENTS (ADDED WITHOUT DRIFT)
    # ========================================================
    "vpn_connect": {
        "patterns": [
            r"(connect|enable|turn on) vpn$",
            r"vpn on$",
            r"tailscale up$",
        ],
        "description": "Connect VPN via Tailscale.",
    },
    "vpn_disconnect": {
        "patterns": [
            r"(disconnect|disable|turn off) vpn$",
            r"vpn off$",
            r"tailscale down$",
        ],
        "description": "Disconnect VPN via Tailscale.",
    },
    "vpn_status": {
        "patterns": [
            r"(vpn|tailscale) status$",
            r"am i on vpn$",
            r"am i connected to vpn$",
        ],
        "description": "Show VPN status.",
    },
}


def _match_patterns(text: str, patterns: list[str]) -> Optional[re.Match]:
    for p in patterns:
        m = re.match(p, text)
        if m:
            return m
    return None


# ============================================================
# 4. ARGUMENT EXTRACTORS (UNCHANGED)
# ============================================================

def extract_reset_state(_: re.Match) -> Dict[str, Any]:
    return {}


def extract_show_plan(_: re.Match) -> Dict[str, Any]:
    return {}


def extract_show_goals(_: re.Match) -> Dict[str, Any]:
    return {}


def extract_add_step(match: re.Match) -> Dict[str, Any]:
    desc = match.group(3).strip()
    return {"description": desc}


def extract_complete_step(match: re.Match) -> Dict[str, Any]:
    nums = [g for g in match.groups() if g and g.isdigit()]
    if nums:
        return {"step_number": int(nums[0])}
    return {"step_number": None}


def extract_create_goal(match: re.Match) -> Dict[str, Any]:
    name: Optional[str] = None
    try:
        name = match.group(5)
    except Exception:
        try:
            name = match.group(1)
        except Exception:
            name = None

    if name:
        name = name.strip()

    return {"name": name}


def extract_switch_goal(match: re.Match) -> Dict[str, Any]:
    nums = [g for g in match.groups() if g and g.isdigit()]
    if nums:
        return {"goal_id": int(nums[0])}
    return {"goal_id": None}


def extract_delete_step(match: re.Match) -> Dict[str, Any]:
    nums = [g for g in match.groups() if g and g.isdigit()]
    if nums:
        return {"step_number": int(nums[0])}
    return {"step_number": None}


def extract_rename_step(match: re.Match) -> Dict[str, Any]:
    nums = [g for g in match.groups() if g and g.isdigit()]
    if nums:
        step_num = int(nums[0])
        new_desc = match.group(2).strip()
        return {"step_number": step_num, "description": new_desc}

    new_desc = match.group(2).strip()
    return {"step_number": None, "description": new_desc}


# NEW: VPN extractors (no args needed)
def extract_vpn_connect(_: re.Match) -> Dict[str, Any]:
    return {}


def extract_vpn_disconnect(_: re.Match) -> Dict[str, Any]:
    return {}


def extract_vpn_status(_: re.Match) -> Dict[str, Any]:
    return {}


EXTRACTORS: Dict[str, Callable[[re.Match], Dict[str, Any]]] = {
    "reset_state": extract_reset_state,
    "show_plan": extract_show_plan,
    "show_goals": extract_show_goals,
    "add_step": extract_add_step,
    "complete_step": extract_complete_step,
    "create_goal": extract_create_goal,
    "switch_goal": extract_switch_goal,
    "delete_step": extract_delete_step,
    "rename_step": extract_rename_step,

    # NEW: VPN extractors
    "vpn_connect": extract_vpn_connect,
    "vpn_disconnect": extract_vpn_disconnect,
    "vpn_status": extract_vpn_status,
}


# ============================================================
# 5. WATCHPOINT + DEBUG PATTERNS
# ============================================================

WATCHPOINT_PATTERNS = {
    "add_watchpoint": [
        r"watch (.+)$",
    ],
    "remove_watchpoint": [
        r"unwatch (.+)$",
    ],
    "list_watchpoints": [
        r"(list|show) watchpoints$",
    ],
}

DEBUG_PATTERNS: Dict[str, list[str]] = {
    "debug_state": [
        r"debug state$",
        r"show raw state$",
        r"print state$",
    ],
    "debug_goals": [
        r"debug goals$",
        r"show raw goals$",
        r"print goals$",
    ],
    "debug_steps": [
        r"debug steps$",
        r"show raw steps$",
        r"print steps$",
    ],
    "debug_raw": [
        r"debug raw$",
        r"show everything$",
        r"dump all$",
    ],
    "debug_last": [
        r"debug last$",
    ],
    "debug_diff": [
        r"debug diff$",
        r"debug state diff$",
    ],
    "debug_context": [
        r"debug context$",
    ],
    "debug_timing": [
        r"debug timing$",
    ],
    "debug_context_trace": [
        r"debug context trace$",
        r"show context trace$",
    ],
    "debug_history": [
        r"debug history$",
        r"show history$",
    ],
    "debug_watch_alerts": [
        r"debug watch alerts$",
        r"show watch alerts$",
    ],
    "debug_semantic_contextual": [
        r"debug semantic contextual$",
    ],
}


# ============================================================
# 6. HELP + DEBUG DETECTION
# ============================================================

HELP_PATTERNS = [
    r"help$",
    r"help (.+)$",
    r"what can you do$",
    r"what commands are available$",
]


def detect_help(text: str) -> Optional[Dict[str, Any]]:
    for p in HELP_PATTERNS:
        m = re.match(p, text)
        if m:
            topic: Optional[str] = None
            try:
                topic = m.group(1).strip()
            except Exception:
                topic = None
            return {"intent": "help", "args": {"topic": topic}, "raw": text}
    return None


def detect_debug(text: str) -> Optional[Dict[str, Any]]:
    for intent, patterns in DEBUG_PATTERNS.items():
        for p in patterns:
            if re.match(p, text):
                return {"intent": intent, "args": {}, "raw": text}
    return None


# ============================================================
# 7. ADAPT TO COMMAND (REQUIRED BY REPL)
# ============================================================

def adapt_to_command(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified entry point for the REPL pipeline.
    Wraps legacy intent detection + debug + help + watchpoints.
    """

    clean = normalize(expand_aliases(text))

    # Debug commands
    dbg = detect_debug(clean)
    if dbg:
        return dbg

    # Help commands
    help_cmd = detect_help(clean)
    if help_cmd:
        return help_cmd

    # Watchpoint commands
    for intent, patterns in WATCHPOINT_PATTERNS.items():
        for p in patterns:
            m = re.match(p, clean)
            if m:
                return {"intent": intent, "args": {"path": m.group(1)}, "raw": text}

    # Legacy intents
    for intent, info in INTENT_PATTERNS.items():
        match = _match_patterns(clean, info["patterns"])
        if match:
            extractor = EXTRACTORS.get(intent)
            args = extractor(match) if extractor else {}
            return {"intent": intent, "args": args, "raw": text}

    # Unknown
    return {"intent": "unknown", "args": {"raw": text}, "raw": text}


# ============================================================
# 8. HANDLE COMMAND (REQUIRED BY REPL)
# ============================================================

def handle_command(
    cmd: Dict[str, Any],
    state: Dict[str, Any],
    execution,
    goal_manager,
    plan_renderer,
    dashboard,
    plan_mode: str,
):
    """
    REPL 3.0 calls this after NLU + Firewall + ContextResolver.
    """

    intent = cmd.get("intent")

    # Structured commands (registered via decorator)
    if intent in COMMAND_REGISTRY:
        handler = COMMAND_REGISTRY[intent]["handler"]
        return handler(
            state=state,
            execution=execution,
            goal_manager=goal_manager,
            plan_renderer=plan_renderer,
            dashboard=dashboard,
            plan_mode=plan_mode,
            args=cmd.get("args", {}),
        )

    # Legacy commands (execution engine)
    return execution.execute(cmd, state)
