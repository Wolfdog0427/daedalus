# runtime/debug_cockpit.py

from typing import Any, Dict, List, Optional

# Optional: integrate with existing debug_tools if present
try:
    from . import debug_tools as dt
except Exception:  # pragma: no cover - optional dependency
    dt = None  # type: ignore


# ------------------------------------------------------------
# ANSI color helpers
# ------------------------------------------------------------

class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    FG_RED = "\033[31m"
    FG_GREEN = "\033[32m"
    FG_YELLOW = "\033[33m"
    FG_BLUE = "\033[34m"
    FG_MAGENTA = "\033[35m"
    FG_CYAN = "\033[36m"
    FG_WHITE = "\033[37m"

    @staticmethod
    def color(text: str, color: str) -> str:
        return f"{color}{text}{Ansi.RESET}"

    @staticmethod
    def bold(text: str) -> str:
        return f"{Ansi.BOLD}{text}{Ansi.RESET}"


# ------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------

def _format_section(title: str, body: str, color: str = Ansi.FG_CYAN) -> str:
    line = Ansi.color(Ansi.bold(f"=== {title} ==="), color)
    return f"{line}\n{body}\n"


def _format_dict(d: Any) -> str:
    if dt and hasattr(dt, "pretty_json"):
        try:
            return dt.pretty_json(d)  # type: ignore[attr-defined]
        except Exception:
            pass
    # Fallback: simple repr
    return repr(d)


def _format_list(lines: List[str]) -> str:
    return "\n".join(lines)


# ------------------------------------------------------------
# DebugCockpit
# ------------------------------------------------------------

class DebugCockpit:
    """
    Unified debug cockpit for the full pipeline:

        - Raw input
        - NLU interpretation
        - Semantic repairs
        - Firewall repairs (if provided)
        - Context resolver trace
        - Final executable command
        - State before/after (optional)
        - Timing (optional)
        - Watch alerts / history (optional)

    This is a pure formatter/orchestrator. You feed it the pieces
    from your REPL/dispatcher, and it returns a single, readable view.
    """

    def __init__(self) -> None:
        pass

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def render_pipeline_view(self, ctx: Dict[str, Any]) -> str:
        """
        ctx is a dict that can contain:

            raw_input: str
            nlu: dict
            firewall_cmd: dict or None
            resolved_cmd: dict or None
            final_cmd: dict or None

            resolver_trace: str or List[str] or None
            semantic_repairs: dict or None  (from intent classifier)
            firewall_repairs: dict or None  (from firewall, if any)

            state_before: dict or None
            state_after: dict or None

            timing: dict or None
            history: list or None
            watch_alerts: list or None

        Only the fields you provide will be shown.
        """

        sections: List[str] = []

        # 1. Raw input
        raw_input = ctx.get("raw_input")
        if raw_input is not None:
            sections.append(
                _format_section(
                    "RAW INPUT",
                    Ansi.color(repr(raw_input), Ansi.FG_WHITE),
                    Ansi.FG_BLUE,
                )
            )

        # 2. NLU interpretation
        nlu = ctx.get("nlu")
        if nlu is not None:
            body_lines: List[str] = []

            canonical_intent = nlu.get("canonical_intent")
            verb_family = nlu.get("verb_family")
            object_family = nlu.get("object_family")
            normalized_text = nlu.get("normalized_text")

            body_lines.append(
                Ansi.color(f"canonical_intent: {canonical_intent}", Ansi.FG_GREEN)
            )
            body_lines.append(f"verb_family: {verb_family}")
            body_lines.append(f"object_family: {object_family}")
            body_lines.append(f"normalized_text: {repr(normalized_text)}")

            step_number = nlu.get("step_number")
            goal_number = nlu.get("goal_number")
            if step_number is not None:
                body_lines.append(f"step_number: {step_number}")
            if goal_number is not None:
                body_lines.append(f"goal_number: {goal_number}")

            vague_step = nlu.get("vague_step")
            vague_goal = nlu.get("vague_goal")
            if vague_step:
                body_lines.append(Ansi.color("vague_step: True", Ansi.FG_YELLOW))
            if vague_goal:
                body_lines.append(Ansi.color("vague_goal: True", Ansi.FG_YELLOW))

            # Semantic repairs from classifier
            sem_repairs = nlu.get("semantic_repairs") or ctx.get("semantic_repairs")
            if sem_repairs:
                body_lines.append("")
                body_lines.append(Ansi.color("Semantic repairs:", Ansi.FG_CYAN))
                body_lines.append(_format_dict(sem_repairs))

            sections.append(
                _format_section(
                    "NLU INTERPRETATION",
                    _format_list(body_lines),
                    Ansi.FG_GREEN,
                )
            )

        # 3. Firewall repairs (if any)
        firewall_repairs = ctx.get("firewall_repairs")
        if firewall_repairs:
            sections.append(
                _format_section(
                    "FIREWALL REPAIRS",
                    _format_dict(firewall_repairs),
                    Ansi.FG_MAGENTA,
                )
            )

        # 4. Resolver trace
        resolver_trace = ctx.get("resolver_trace")
        if resolver_trace:
            if isinstance(resolver_trace, list):
                trace_body = _format_list(resolver_trace)
            else:
                trace_body = str(resolver_trace)
            sections.append(
                _format_section(
                    "CONTEXT RESOLVER TRACE",
                    trace_body,
                    Ansi.FG_CYAN,
                )
            )

        # 5. Commands at each stage
        firewall_cmd = ctx.get("firewall_cmd")
        resolved_cmd = ctx.get("resolved_cmd")
        final_cmd = ctx.get("final_cmd")

        if firewall_cmd is not None:
            sections.append(
                _format_section(
                    "COMMAND AFTER FIREWALL",
                    _format_dict(firewall_cmd),
                    Ansi.FG_YELLOW,
                )
            )

        if resolved_cmd is not None:
            sections.append(
                _format_section(
                    "COMMAND AFTER CONTEXT RESOLVER",
                    _format_dict(resolved_cmd),
                    Ansi.FG_YELLOW,
                )
            )

        if final_cmd is not None:
            sections.append(
                _format_section(
                    "FINAL EXECUTABLE COMMAND",
                    _format_dict(final_cmd),
                    Ansi.FG_GREEN,
                )
            )

        # 6. State before/after
        state_before = ctx.get("state_before")
        state_after = ctx.get("state_after")

        if state_before is not None:
            sections.append(
                _format_section(
                    "STATE BEFORE",
                    _format_dict(state_before),
                    Ansi.FG_BLUE,
                )
            )

        if state_after is not None:
            sections.append(
                _format_section(
                    "STATE AFTER",
                    _format_dict(state_after),
                    Ansi.FG_BLUE,
                )
            )

        # 7. Timing
        timing = ctx.get("timing")
        if timing is not None:
            sections.append(
                _format_section(
                    "TIMING",
                    _format_dict(timing),
                    Ansi.FG_MAGENTA,
                )
            )

        # 8. Watch alerts
        watch_alerts = ctx.get("watch_alerts")
        if watch_alerts:
            sections.append(
                _format_section(
                    "WATCH ALERTS",
                    _format_dict(watch_alerts),
                    Ansi.FG_RED,
                )
            )

        # 9. History
        history = ctx.get("history")
        if history:
            sections.append(
                _format_section(
                    "HISTORY (RECENT)",
                    _format_dict(history),
                    Ansi.FG_WHITE,
                )
            )

        # Join all sections
        return "\n".join(sections)


# ------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------

def debug_pipeline_view(ctx: Dict[str, Any]) -> str:
    """
    Convenience wrapper so you can call:

        from .debug_cockpit import debug_pipeline_view

        print(debug_pipeline_view({
            "raw_input": text,
            "nlu": nlu_result,
            "firewall_cmd": firewall_cmd,
            "resolved_cmd": resolved_cmd,
            "final_cmd": final_cmd,
            "resolver_trace": resolver.get_last_trace(),
            "state_before": state_before,
            "state_after": state_after,
            "timing": timing_info,
            "history": history,
            "watch_alerts": watch_alerts,
        }))

    You control how much you pass in.
    """
    cockpit = DebugCockpit()
    return cockpit.render_pipeline_view(ctx)
