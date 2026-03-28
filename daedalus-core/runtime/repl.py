# runtime/repl.py

"""
REPL 3.0 — Hybrid Command + Full Debug Cockpit

- Preserves legacy natural-language commands:
    add goal X
    add step Y
    show plan
    debug raw

- Adds structured / hierarchical commands:
    goal add "System Test"
    step add "Initialize"
    plan show
    goals list
    goals archive <id>
    goals unarchive <id>

- Integrates full pipeline:
    InputGateway  →  SemanticFirewall  →  ContextResolver  →  ContextualResolver
    →  ExecutionEngine / GoalManager  →  PlanRenderer / DashboardRenderer

- Integrates debug cockpit:
    debug nlu <text>
    debug state
    debug diff
    debug context
    debug history
    debug cockpit on/off
    debug pipeline <text>
"""

from typing import Dict, Any, Optional, Tuple
import copy
import os

try:
    import readline  # noqa: F401 — enables arrow-key history in input()
except ImportError:
    pass

# --- Execution Layer ---
from runtime.execution.execution import ExecutionEngine
from runtime.execution.goal_manager import GoalManager

# --- Interpretation Layer ---
from runtime.context_resolver import ContextResolver
from runtime.contextual_resolver import ContextualResolver

# --- Debug Layer ---
from runtime.debug_tools import DebugState
from runtime.nlu_debug import debug_nlu_pipeline
from runtime.pretty import (
    pretty_debug_state,
    pretty_debug_diff,
    pretty_debug_context,
)
from runtime.history_timeline import pretty_debug_history
from runtime.debug_cockpit import debug_pipeline_view

# --- Persistence Layer ---
from runtime.state_store import StateStore

# --- Rendering Layer ---
from runtime.plan_renderer import PlanRenderer
from runtime.goal_dashboard_renderer import GoalDashboardRenderer

# --- Input & Safety Layer ---
from runtime.input_gateway import InputGateway
from runtime.semantic_firewall import SemanticFirewall
from runtime.self_test import run_background_self_test
from runtime.watch_monitor import analyze_last_action_for_watch_anomalies
from runtime.fallback_manager import is_enabled
from runtime.feature_flags import is_enabled as feature_flag_enabled

# --- Command System ---
from runtime.command_router import (
    COMMAND_REGISTRY,
    register_command,
    dispatch_command,
    handle_command,
)

# --- NLU Resolver Adapter ---
from nlu.resolver_adapter import adapt_to_command

# --- REPL Context ---
from runtime.repl_context import REPLContext, build_context as _build_context

# --- Self-healing / Orchestrator / Diagnostics ---
from core.contracts import CockpitSnapshot
from diagnostics.realtime_diagnoser import RealtimeDiagnoser, FailureReport
from orchestrator.orchestrator import SelfHealingOrchestrator
from security.code_integrity import CodeIntegrity
from config.security_config import REPO_ROOT, INTEGRITY_STORAGE_ROOT
from versioning.version_manager import VersionManager
from versioning.file_version_manager import FileVersionManager

# --- Failure History / Patterns ---
from runtime.failure_history import FailureHistory


# ------------------------------------------------------------
# SELF-HEALING SINGLETONS
# ------------------------------------------------------------

_code_integrity = CodeIntegrity(REPO_ROOT, INTEGRITY_STORAGE_ROOT)
_version_manager: VersionManager = FileVersionManager(
    repo_root=REPO_ROOT,
    storage_root=os.path.join(REPO_ROOT, ".versions"),
)
_orchestrator = SelfHealingOrchestrator(_code_integrity, _version_manager)
_diagnoser = RealtimeDiagnoser()

_failure_history = FailureHistory(
    os.path.join(REPO_ROOT, "logs", "failure_history.jsonl")
)


# ------------------------------------------------------------
# SYSTEM / HEALTH COMMANDS
# ------------------------------------------------------------

def handle_system_health(context: REPLContext) -> str:
    return context.system_health()


@register_command(
    "system.doctor",
    aliases=["run doctor", "system doctor"],
    nl_patterns=[
        "run the doctor",
        "start the doctor",
    ],
)
def _cmd_system_doctor(context: REPLContext) -> str:
    return context.run_doctor()


@register_command(
    "system.failures",
    aliases=["system failures", "system.failures recent"],
    nl_patterns=[
        "show recent failures",
        "show system failures",
    ],
)
def _cmd_system_failures(context: REPLContext) -> str:
    # Context not needed; kept for symmetry with other commands
    return _failure_history.pretty_recent(20)


@register_command(
    "system.failures.patterns",
    aliases=["system failures patterns", "system.failures patterns"],
    nl_patterns=[
        "show failure patterns",
        "show system failure patterns",
    ],
)
def _cmd_system_failure_patterns(context: REPLContext) -> str:
    return _failure_history.pretty_patterns()


# ------------------------------------------------------------
# VERSIONING COMMANDS
# ------------------------------------------------------------

@register_command(
    "system.versions",
    aliases=["system versions", "versions"],
    nl_patterns=[
        "show versions",
        "list versions",
    ],
)
def _cmd_system_versions(context: REPLContext) -> str:
    pretty = getattr(_version_manager, "pretty_versions", None)
    if callable(pretty):
        return pretty()
    return "Version manager does not support listing versions."


@register_command(
    "system.version.snapshot",
    aliases=["snapshot version", "save version"],
    nl_patterns=[
        "snapshot system",
        "save system version",
    ],
)
def _cmd_system_snapshot(context: REPLContext) -> str:
    vid = _version_manager.snapshot_lkg("manual snapshot")
    return f"Created version snapshot: {vid}"


@register_command(
    "system.version.rollback",
    aliases=["rollback version"],
    nl_patterns=[
        "rollback to version",
    ],
)
def _cmd_system_rollback(context: REPLContext) -> str:
    parts = context.raw_input.split()
    if len(parts) < 3:
        return "Usage: system.version.rollback <version_id>"
    vid = parts[-1]
    _version_manager.rollback_to(vid)
    return f"Rolled back logical LKG to: {vid}"


@register_command(
    "system.candidates",
    aliases=["candidates", "system candidates"],
    nl_patterns=[
        "show candidates",
        "list candidates",
    ],
)
def _cmd_system_candidates(context: REPLContext) -> str:
    pretty = getattr(_version_manager, "pretty_candidates", None)
    if callable(pretty):
        return pretty()
    return "Version manager does not support listing candidates."


# ------------------------------------------------------------
# PROMPT BUILDER
# ------------------------------------------------------------

def _build_prompt(state: Dict[str, Any]) -> str:
    active_goal_id = state.get("active_goal_id")
    steps = state.get("steps") or []

    if not active_goal_id:
        return "> "

    next_step_id: Optional[int] = None
    for step in steps:
        if step.get("goal_id") == active_goal_id and not step.get("done"):
            next_step_id = step.get("id")
            break

    if next_step_id is not None:
        return f"[g{active_goal_id}:s{next_step_id}] > "
    else:
        return f"[g{active_goal_id}] > "


# ------------------------------------------------------------
# HYBRID COMMAND PARSER
# ------------------------------------------------------------

def _handle_hierarchical_commands(
    lower: str,
    user_input: str,
    state: Dict[str, Any],
    execution: ExecutionEngine,
    goal_manager: GoalManager,
    context_resolver: ContextResolver,
    contextual_resolver: ContextualResolver,
    debug_state: DebugState,
    store: StateStore,
    plan_renderer: PlanRenderer,
    dashboard: GoalDashboardRenderer,
    plan_mode: str,
    dashboard_sort: str,
    dashboard_filter: str,
) -> Optional[Tuple[str, str, str]]:

    # GOAL ADD
    if lower.startswith("goal add "):
        payload = user_input[len("goal add "):].strip()
        return _run_pipeline(
            f"add goal {payload}",
            state, execution, goal_manager,
            context_resolver, contextual_resolver,
            debug_state, store, plan_renderer, dashboard,
            plan_mode, dashboard_sort, dashboard_filter,
        )

    # STEP ADD
    if lower.startswith("step add "):
        payload = user_input[len("step add "):].strip()
        return _run_pipeline(
            f"add step {payload}",
            state, execution, goal_manager,
            context_resolver, contextual_resolver,
            debug_state, store, plan_renderer, dashboard,
            plan_mode, dashboard_sort, dashboard_filter,
        )

    # PLAN SHOW
    if lower in ("plan show", "show plan"):
        return _run_pipeline(
            "show plan",
            state, execution, goal_manager,
            context_resolver, contextual_resolver,
            debug_state, store, plan_renderer, dashboard,
            plan_mode, dashboard_sort, dashboard_filter,
        )

    # GOALS LIST
    if lower in ("goals list", "list goals"):
        return _run_pipeline(
            "list goals",
            state, execution, goal_manager,
            context_resolver, contextual_resolver,
            debug_state, store, plan_renderer, dashboard,
            plan_mode, dashboard_sort, dashboard_filter,
        )

    # GOALS ARCHIVE
    if lower.startswith("goals archive "):
        try:
            gid = int(user_input[len("goals archive "):].strip())
        except ValueError:
            print("Usage: goals archive <id>")
            return plan_mode, dashboard_sort, dashboard_filter

        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.archive_goal(gid))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    # GOALS UNARCHIVE
    if lower.startswith("goals unarchive "):
        try:
            gid = int(user_input[len("goals unarchive "):].strip())
        except ValueError:
            print("Usage: goals unarchive <id>")
            return plan_mode, dashboard_sort, dashboard_filter

        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.unarchive_goal(gid))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    return None


# ------------------------------------------------------------
# PIPELINE RUNNER (WITH SELF-DIAGNOSIS + ERROR DETECTION)
# ------------------------------------------------------------

def _run_pipeline(
    user_input: str,
    state: Dict[str, Any],
    execution: ExecutionEngine,
    goal_manager: GoalManager,
    context_resolver: ContextResolver,
    contextual_resolver: ContextualResolver,
    debug_state: DebugState,
    store: StateStore,
    plan_renderer: PlanRenderer,
    dashboard: GoalDashboardRenderer,
    plan_mode: str,
    dashboard_sort: str,
    dashboard_filter: str,
    *,
    cockpit_debug: bool = False,
) -> Tuple[str, str, str]:

    # Snapshot domain-relevant state before (skip history to avoid quadratic growth)
    state_before = copy.deepcopy({
        k: v for k, v in state.items()
        if k not in ("history",) and not k.startswith("_")
    })

    clean_text, sanitize_report, hostility_score = InputGateway.sanitize(user_input)
    lower = clean_text.lower().strip()

    # Error tracking
    error_type: str = ""
    error_message: str = ""
    error_subsystem: str = ""
    error_stage: str = ""

    # Special-case: debug nlu <text>
    if lower.startswith("debug nlu "):
        payload = clean_text[len("debug nlu "):].strip()
        debug_nlu_pipeline(payload, state)
        return plan_mode, dashboard_sort, dashboard_filter

    raw_cmd = None
    firewall_cmd = None
    resolved_cmd = None
    final_cmd = None
    result: Optional[str] = None

    # --- NLU stage ---
    try:
        raw_cmd = adapt_to_command(clean_text, state)
    except Exception as e:
        error_type = "nlu_error"
        error_message = str(e)
        error_subsystem = "nlu"
        error_stage = "nlu"
        result = (
            "❗ Error: Unable to understand command.\n"
            "(NLU error: unable to adapt input to command)"
        )

    if debug_state.nlu and raw_cmd is not None:
        debug_nlu_pipeline(clean_text, state)

    # --- Firewall stage ---
    if not error_type:
        try:
            firewall_cmd = SemanticFirewall.firewall(raw_cmd, state)
        except Exception as e:
            error_type = "firewall_error"
            error_message = str(e)
            error_subsystem = "firewall"
            error_stage = "firewall"
            result = (
                "❗ Error: Command blocked by safety layer.\n"
                "(Firewall error: command could not be safely processed)"
            )

    # --- Context resolver stage ---
    if not error_type:
        try:
            resolved_cmd = context_resolver.resolve(firewall_cmd, state)
        except Exception as e:
            error_type = "resolver_error"
            error_message = str(e)
            error_subsystem = "resolver"
            error_stage = "context_resolver"
            result = (
                "❗ Error: Unable to resolve command.\n"
                "(Resolver mismatch: context resolution failed)"
            )

    # --- Contextual resolver stage ---
    if not error_type:
        try:
            final_cmd = contextual_resolver.resolve(resolved_cmd, state)
        except Exception as e:
            error_type = "resolver_error"
            error_message = str(e)
            error_subsystem = "resolver"
            error_stage = "contextual_resolver"
            result = (
                "❗ Error: Unable to resolve command.\n"
                "(Resolver mismatch: missing or invalid handler)"
            )

    # --- Execution stage ---
    if not error_type:
        try:
            result = handle_command(
                final_cmd, state, execution, goal_manager,
                plan_renderer, dashboard, plan_mode,
            )
            # Soft failure detection: unknown/invalid command patterns
            if isinstance(result, str):
                lower_res = result.lower()
                if "unknown command" in lower_res or "unrecognized command" in lower_res:
                    error_type = "invalid_command"
                    error_message = result
                    error_subsystem = "command_router"
                    error_stage = "handle_command"
                    result = (
                        "❗ Error: Unknown command.\n"
                        "(Invalid command: not recognized by command router)"
                    )
        except Exception as e:
            error_type = "execution_error"
            error_message = str(e)
            error_subsystem = "execution"
            error_stage = "handle_command"
            result = (
                "❗ Error: Command failed during execution.\n"
                "(Execution error: handler raised an exception)"
            )

    # Ensure we have some result string
    if result is None:
        result = ""

    # Compute watchpoint changes before recording
    watch_changes = None
    try:
        watchpoints = state.get("watchpoints", [])
        if watchpoints:
            watch_changes = []
            for wp in watchpoints:
                before_val = state_before.get(wp)
                after_val = state.get(wp)
                if before_val != after_val:
                    watch_changes.append({
                        "path": wp,
                        "before": copy.deepcopy(before_val),
                        "after": copy.deepcopy(after_val),
                    })
            if not watch_changes:
                watch_changes = None
    except Exception:
        watch_changes = None

    # Save debug state for introspection commands
    state["last_nlu_cmd"] = copy.deepcopy(raw_cmd) if raw_cmd else {}
    ctx_trace = contextual_resolver.get_last_trace() if contextual_resolver else []
    state["contextual_trace"] = copy.deepcopy(ctx_trace) if ctx_trace else []
    state["_before_last_cmd"] = copy.deepcopy(firewall_cmd or raw_cmd or {})
    state["_after_last_cmd"] = copy.deepcopy(final_cmd or resolved_cmd or {})

    # Record action even on failure (best-effort)
    try:
        entry = store.record_action(
            user_input,
            final_cmd or resolved_cmd or firewall_cmd or raw_cmd or {},
            result,
            context_trace=ctx_trace,
            nlu_cmd=raw_cmd,
            command_before=state_before,
            state=state,
            watch_changes=watch_changes,
        )
        # Sync a lightweight summary into the live state dict (skip state snapshot)
        summary = {k: v for k, v in entry.items() if k != "state"}
        state.setdefault("history", []).append(summary)
        store.save(state)
    except Exception:
        pass

    if feature_flag_enabled("background_self_test"):
        run_background_self_test()
    analyze_last_action_for_watch_anomalies(store)

    # Snapshot after for cockpit / state delta
    state_after = state
    state_changed = state_before != state_after
    changed_keys = [
        k for k in state_after.keys()
        if state_before.get(k) != state_after.get(k)
    ]

    # Cockpit view (one-shot or persistent)
    if cockpit_debug or getattr(debug_state, "cockpit", False):
        ctx = {
            "raw_input": user_input,
            "clean_input": clean_text,
            "sanitize_report": sanitize_report,
            "hostility_score": hostility_score,
            "nlu": raw_cmd,
            "firewall_cmd": firewall_cmd,
            "resolved_cmd": resolved_cmd,
            "final_cmd": final_cmd,
            "state_before": state_before,
            "state_after": state_after,
        }
        print(debug_pipeline_view(ctx))

    # Normal pipeline / error output
    if result:
        print(result)

    # --------------------------------------------------------
    # SELF-DIAGNOSIS: build enriched cockpit snapshot
    # --------------------------------------------------------
    def _safe_attr(obj: Any, name: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    snapshot: CockpitSnapshot = {
        # Core interaction
        "user_input": user_input,
        "clean_input": clean_text,
        "parsed_intent": str(raw_cmd),
        "resolver_target": str(final_cmd),
        "result": result,

        # NLU metadata (best-effort)
        "nlu_repr": repr(raw_cmd),
        "nlu_intent": _safe_attr(raw_cmd, "intent", None),
        "nlu_entities": _safe_attr(raw_cmd, "entities", None),
        "nlu_confidence": _safe_attr(raw_cmd, "confidence", None),
        "nlu_ambiguous": _safe_attr(raw_cmd, "ambiguous", None),

        # Firewall metadata
        "firewall_repr": repr(firewall_cmd),
        "firewall_allowed": _safe_attr(firewall_cmd, "allowed", None),
        "firewall_reason": _safe_attr(firewall_cmd, "reason", None),

        # Resolver metadata
        "resolved_repr": repr(resolved_cmd),
        "resolver_rule": _safe_attr(resolved_cmd, "rule", None),
        "resolver_fallback": _safe_attr(resolved_cmd, "fallback", None),

        # Contextual resolver / handler metadata
        "final_repr": repr(final_cmd),
        "handler_name": _safe_attr(final_cmd, "handler_name", None),
        "handler_module": _safe_attr(final_cmd, "handler_module", None),

        # Safety / input metadata
        "sanitize_report": sanitize_report,
        "hostility_score": hostility_score,

        # State delta metadata
        "state_changed": state_changed,
        "changed_keys": changed_keys,

        # Error metadata
        "error_type": error_type,
        "error_message": error_message,
        "subsystem": error_subsystem or "pipeline",
        "pipeline_stage": error_stage or "post_execute",
    }

    failure_report: Optional[FailureReport] = None
    proposal = None
    plan = None

    try:
        failure_report = _diagnoser.analyze_interaction(snapshot)
    except Exception:
        failure_report = None

    if failure_report:
        try:
            proposal = _diagnoser.propose_fix(failure_report)
            fix_request = _orchestrator.proposal_to_fix_request(proposal)
            plan = _orchestrator.plan_improvement(fix_request)

            # Store candidate + auto snapshot as a milestone
            try:
                _version_manager.store_candidate(proposal)
                reason = f"auto: {proposal.proposal_type} - {proposal.description}"
                _version_manager.snapshot_lkg(reason)
            except Exception:
                pass

            print("\n[Self-diagnosis]")
            print(f"  Failure:          {failure_report.failure_type}")
            print(f"  Subsystem:        {failure_report.details.get('subsystem')}")
            print(f"  Stage:            {failure_report.details.get('pipeline_stage')}")
            print(f"  Proposed fix:     {proposal.description}")
            print(f"  Change type:      {proposal.proposal_type}")
            print(f"  Expected benefit: {proposal.expected_benefit}")
            print(f"  Plan budget:      {plan.change_budget_files} files, {plan.change_budget_lines} lines")
        except Exception:
            pass

    # Record failure history (even if diagnoser didn't fire, if there was an error)
    try:
        if error_type or failure_report:
            _failure_history.record(snapshot, failure_report, proposal, plan)
    except Exception:
        pass

    return plan_mode, dashboard_sort, dashboard_filter


# ------------------------------------------------------------
# LINE PROCESSOR
# ------------------------------------------------------------

def _process_line(
    user_input: str,
    state: Dict[str, Any],
    execution: ExecutionEngine,
    goal_manager: GoalManager,
    context_resolver: ContextResolver,
    contextual_resolver: ContextualResolver,
    debug_state: DebugState,
    store: StateStore,
    plan_renderer: PlanRenderer,
    dashboard: GoalDashboardRenderer,
    plan_mode: str,
    dashboard_sort: str,
    dashboard_filter: str,
) -> Tuple[str, str, str]:

    lower = user_input.lower().strip()

    # EXIT
    if lower in ("exit", "quit"):
        raise SystemExit

    # NOTIFICATIONS
    if lower in ("notifications", "show notifications", "notifs"):
        try:
            from runtime.notification_center import list_unread, list_all
            show_all = lower == "show notifications"
            items = list_all() if show_all else list_unread()
            if not items:
                print("📬 No notifications." if show_all else "📬 No unread notifications.")
            else:
                print(f"📬 {len(items)} notification(s):\n")
                for n in items:
                    ts = n.get("timestamp", "")
                    cat = n.get("category", "info")
                    msg = n.get("message", "")
                    nid = n.get("id", "?")
                    print(f"  [{cat.upper()}] {msg}  (id: {nid}, {ts})")
        except Exception as exc:
            print(f"⚠ Could not load notifications: {exc}")
        return plan_mode, dashboard_sort, dashboard_filter

    # NL SHORTCUTS (undo, redo, checkpoints, navigation — fast path)
    try:
        from runtime.shortcuts import resolve_shortcut
        shortcut = resolve_shortcut(user_input)
        if shortcut is not None:
            return _run_pipeline(
                shortcut.get("intent", user_input),
                state, execution, goal_manager,
                context_resolver, contextual_resolver,
                debug_state, store, plan_renderer, dashboard,
                plan_mode, dashboard_sort, dashboard_filter,
            )
    except ImportError:
        pass

    # COMMAND REGISTRY
    dispatched = dispatch_command(user_input)
    if dispatched and dispatched in COMMAND_REGISTRY:
        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        handler = COMMAND_REGISTRY[dispatched].get("handler")
        if handler:
            print(handler(context))
            return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    # PLAN MODE
    if lower == "plan mode":
        print(f"Current plan mode: {plan_mode}")
        return plan_mode, dashboard_sort, dashboard_filter

    if lower.startswith("plan mode "):
        mode = lower[len("plan mode "):].strip()
        if mode in ("pretty", "tree", "compact"):
            print(f"Plan mode set to: {mode}")
            return mode, dashboard_sort, dashboard_filter
        print("Invalid plan mode. Use: pretty, tree, or compact.")
        return plan_mode, dashboard_sort, dashboard_filter

    # GOALS DASHBOARD CONTROLS
    if lower.startswith("goals sort "):
        mode = lower[len("goals sort "):].strip()
        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.set_goals_sort(mode))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    if lower.startswith("goals filter "):
        flt = lower[len("goals filter "):].strip()
        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.set_goals_filter(flt))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    # LEGACY ARCHIVE COMMANDS
    if lower.startswith("archive goal "):
        try:
            gid = int(user_input[len("archive goal "):].strip())
        except ValueError:
            print("Usage: archive goal <id>")
            return plan_mode, dashboard_sort, dashboard_filter

        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.archive_goal(gid))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    if lower.startswith("unarchive goal "):
        try:
            gid = int(user_input[len("unarchive goal "):].strip())
        except ValueError:
            print("Usage: unarchive goal <id>")
            return plan_mode, dashboard_sort, dashboard_filter

        context = _build_context(
            state, execution, goal_manager, store,
            plan_renderer, dashboard, plan_mode,
            dashboard_sort, dashboard_filter,
            debug_state, context_resolver, contextual_resolver,
        )
        print(context.unarchive_goal(gid))
        return context.plan_mode, context.dashboard_sort, context.dashboard_filter

    # DEBUG COCKPIT (existing views)
    if lower == "debug state":
        print(pretty_debug_state(state))
        return plan_mode, dashboard_sort, dashboard_filter

    if lower == "debug diff":
        print(pretty_debug_diff(state))
        return plan_mode, dashboard_sort, dashboard_filter

    if lower == "debug context":
        print(pretty_debug_context(state))
        return plan_mode, dashboard_sort, dashboard_filter

    if lower == "debug history":
        print(pretty_debug_history(state))
        return plan_mode, dashboard_sort, dashboard_filter

    # NEW: cockpit toggle
    if lower == "debug cockpit on":
        debug_state.cockpit = True
        print("Cockpit debug mode: ON")
        return plan_mode, dashboard_sort, dashboard_filter

    if lower == "debug cockpit off":
        debug_state.cockpit = False
        print("Cockpit debug mode: OFF")
        return plan_mode, dashboard_sort, dashboard_filter

    # NEW: one-shot pipeline cockpit
    if lower.startswith("debug pipeline "):
        payload = user_input[len("debug pipeline "):].strip()
        if not payload:
            print("Usage: debug pipeline <text>")
            return plan_mode, dashboard_sort, dashboard_filter

        return _run_pipeline(
            payload, state, execution, goal_manager,
            context_resolver, contextual_resolver, debug_state,
            store, plan_renderer, dashboard,
            plan_mode, dashboard_sort, dashboard_filter,
            cockpit_debug=True,
        )

    # HYBRID COMMANDS
    hybrid = _handle_hierarchical_commands(
        lower, user_input, state, execution, goal_manager,
        context_resolver, contextual_resolver, debug_state,
        store, plan_renderer, dashboard,
        plan_mode, dashboard_sort, dashboard_filter,
    )
    if hybrid is not None:
        return hybrid

    # FALLBACK: full NL pipeline
    return _run_pipeline(
        user_input, state, execution, goal_manager,
        context_resolver, contextual_resolver, debug_state,
        store, plan_renderer, dashboard,
        plan_mode, dashboard_sort, dashboard_filter,
    )


# ------------------------------------------------------------
# ASSISTANT BUILDER
# ------------------------------------------------------------

def build_assistant() -> Tuple[ExecutionEngine, GoalManager]:
    goal_manager = GoalManager()
    execution = ExecutionEngine(goal_manager)
    return execution, goal_manager


# ------------------------------------------------------------
# REPL LOOP
# ------------------------------------------------------------

def run_repl() -> None:
    execution, goal_manager = build_assistant()

    context_resolver = ContextResolver()
    contextual_resolver = ContextualResolver()

    store = StateStore()
    plan_renderer = PlanRenderer()
    dashboard = GoalDashboardRenderer()
    debug_state = DebugState()

    state: Dict[str, Any] = store.load()

    plan_mode = "pretty"
    dashboard_sort = "default"
    dashboard_filter = "all"

    print("Assistant ready. Type 'help' for commands, 'exit' to quit.")
    try:
        from runtime.notification_center import list_unread
        unread = list_unread()
        if unread:
            print(f"\n📬 You have {len(unread)} unread notification(s). Type 'notifications' to view.")
    except Exception:
        pass

    while True:
        try:
            prompt = _build_prompt(state)
            user_input = input(prompt).strip()
            if not user_input:
                continue

            plan_mode, dashboard_sort, dashboard_filter = _process_line(
                user_input, state, execution, goal_manager,
                context_resolver, contextual_resolver, debug_state,
                store, plan_renderer, dashboard,
                plan_mode, dashboard_sort, dashboard_filter,
            )

        except SystemExit:
            print("Goodbye.")
            break
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            if is_enabled("fuzzy_repair"):
                print(f"❗ An error occurred (fallback active): {e}")
            else:
                print(f"❗ An error occurred: {e}")


if __name__ == "__main__":
    run_repl()
