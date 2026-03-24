# runtime/telemetry.py

from __future__ import annotations
from typing import Dict, Any
import time

from governor.singleton import governor
from runtime.system_health_index import system_health_index


class Telemetry:
    """
    System-wide telemetry aggregator.

    Responsibilities:
      - Produce a unified snapshot of system state
      - Expose drift, stability, readiness, tier, behavior, and governor decisions
      - Compute and include long-term system health index
      - Remain passive (no side effects)
    """

    def __init__(self):
        self.cycle_count = 0

    # ------------------------------------------------------------
    # Snapshot Builder
    # ------------------------------------------------------------

    def snapshot(self, cycle_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a full telemetry snapshot for a single cycle.
        """

        self.cycle_count += 1

        drift = cycle_result.get("drift", {})
        stability = cycle_result.get("stability", {})
        readiness = cycle_result.get("readiness", None)

        governor_decision = cycle_result.get("governor_decision", {})
        sho_behavior = cycle_result.get("sho_behavior", {})

        # Build base snapshot
        snapshot = {
            "timestamp": time.time(),
            "cycle": self.cycle_count,

            # Core Metrics
            "metrics": {
                "drift": drift,
                "stability": stability,
                "readiness": readiness,
            },

            # Governor State
            "governor": {
                "tier": cycle_result.get("governor_tier", governor.tier),
                "strict_mode": cycle_result.get("governor_strict_mode", governor.strict_mode),

                # Decision payload
                "decision": governor_decision.get("decision"),
                "reason": governor_decision.get("reason"),

                # Thresholds used during evaluation
                "thresholds": governor_decision.get("thresholds"),

                # Signals used during evaluation
                "signals": governor_decision.get("signals"),

                # Predicted tier transition
                "tier_before": governor_decision.get("tier_before"),
                "tier_after": governor_decision.get("tier_after"),
            },

            # SHO Behavior (tier-based)
            "sho_behavior": sho_behavior,

            # Raw Cycle Result (for debugging)
            "raw_cycle": cycle_result,
        }

        # Compute and attach long-term health index
        health = system_health_index.compute(snapshot)
        snapshot["system_health"] = health

        return snapshot


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
telemetry = Telemetry()


# ------------------------------------------------------------
# Lightweight per-cycle telemetry buffer (Phase 1)
#
# In-memory only — no persistence, no threads.
# ------------------------------------------------------------

from typing import List

_TELEMETRY_BUFFER: List[Dict[str, Any]] = []
_TELEMETRY_MAX = 1000

_SUBSYSTEM_KEYS = ("diagnostics", "governor", "sho", "self_model", "maintenance")


def make_telemetry_record(cycle_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Distill a cycle result from :func:`run_runtime_cycle_once` into a compact
    telemetry record (timestamp + per-subsystem ok/error rollup).
    """
    ts = cycle_result.get("timestamp") or time.time()
    inner = cycle_result.get("results") or {}

    subsystems: Dict[str, str] = {}
    for key in _SUBSYSTEM_KEYS:
        entry = inner.get(key)
        if isinstance(entry, dict) and entry.get("status") == "error":
            subsystems[key] = "error"
        elif isinstance(entry, dict) and "error" in entry:
            subsystems[key] = "error"
        else:
            subsystems[key] = "ok"

    rec: Dict[str, Any] = {"timestamp": ts, "subsystems": subsystems}
    duration = cycle_result.get("duration")
    if isinstance(duration, (int, float)):
        rec["duration"] = duration
    return rec


def record_telemetry(record: Dict[str, Any]) -> None:
    """Append *record* to the in-memory buffer, capping at *_TELEMETRY_MAX*."""
    _TELEMETRY_BUFFER.append(record)
    if len(_TELEMETRY_BUFFER) > _TELEMETRY_MAX:
        del _TELEMETRY_BUFFER[: len(_TELEMETRY_BUFFER) - _TELEMETRY_MAX]


def get_telemetry() -> List[Dict[str, Any]]:
    """Return a shallow copy of the telemetry buffer."""
    return list(_TELEMETRY_BUFFER)


# ------------------------------------------------------------
# Phase 2: history accessors
# ------------------------------------------------------------


def get_recent_telemetry(n: int = 50) -> List[Dict[str, Any]]:
    """Return the last *n* records (or fewer if the buffer is smaller)."""
    if n <= 0:
        return []
    return list(_TELEMETRY_BUFFER[-n:])


def get_telemetry_window(
    start_ts: float, end_ts: float
) -> List[Dict[str, Any]]:
    """Return records whose timestamp falls in [*start_ts*, *end_ts*]."""
    out: List[Dict[str, Any]] = []
    for rec in _TELEMETRY_BUFFER:
        ts = rec.get("timestamp")
        if not isinstance(ts, (int, float)):
            continue
        if start_ts <= ts <= end_ts:
            out.append(rec)
    return out


def summarize_telemetry_window(
    start_ts: float, end_ts: float
) -> Dict[str, Any]:
    """Count records and per-subsystem errors within a time window."""
    window = get_telemetry_window(start_ts, end_ts)
    errors: Dict[str, int] = {k: 0 for k in _SUBSYSTEM_KEYS}
    for rec in window:
        subs = rec.get("subsystems")
        if not isinstance(subs, dict):
            continue
        for key in _SUBSYSTEM_KEYS:
            if subs.get(key) == "error":
                errors[key] += 1
    return {"count": len(window), "errors": errors}


# ------------------------------------------------------------
# Phase 3: trend analysis & stability signals
# ------------------------------------------------------------


def compute_error_rate(n: int = 50) -> Dict[str, Any]:
    """Per-subsystem error rate over the last *n* records."""
    recent = _TELEMETRY_BUFFER[-n:] if n > 0 else []
    total = len(recent)
    rates: Dict[str, float] = {}
    if total == 0:
        rates = {k: 0.0 for k in _SUBSYSTEM_KEYS}
    else:
        counts: Dict[str, int] = {k: 0 for k in _SUBSYSTEM_KEYS}
        for rec in recent:
            subs = rec.get("subsystems")
            if not isinstance(subs, dict):
                continue
            for key in _SUBSYSTEM_KEYS:
                if subs.get(key) == "error":
                    counts[key] += 1
        rates = {k: counts[k] / total for k in _SUBSYSTEM_KEYS}
    return {"window": n, "rates": rates}


def compute_stability_signal(n: int = 50) -> Dict[str, Any]:
    """
    Derived stability indicator over the last *n* records.

    ``stable`` is True when no subsystem exceeds a 20 % error rate.
    This is a descriptive metric — it does not feed into the governor.
    """
    er = compute_error_rate(n)
    rates = er.get("rates") or {}

    recent = _TELEMETRY_BUFFER[-n:] if n > 0 else []
    total = len(recent)

    error_free = 0
    subsystem_errors: Dict[str, int] = {k: 0 for k in _SUBSYSTEM_KEYS}
    for rec in recent:
        subs = rec.get("subsystems")
        if not isinstance(subs, dict):
            continue
        cycle_clean = True
        for key in _SUBSYSTEM_KEYS:
            if subs.get(key) == "error":
                subsystem_errors[key] += 1
                cycle_clean = False
        if cycle_clean:
            error_free += 1

    stable = all(v <= 0.2 for v in rates.values())

    return {
        "window": n,
        "stable": stable,
        "error_free_cycles": error_free,
        "total_cycles": total,
        "subsystem_errors": subsystem_errors,
    }


def compute_sho_trend(n: int = 20) -> Dict[str, Any]:
    """
    Descriptive SHO error trend over the last *n* records.

    Compares the first-5 and last-5 slices of the window to label the
    trend as *improving*, *declining*, or *flat*.
    """
    recent = _TELEMETRY_BUFFER[-n:] if n > 0 else []
    sho_ok = 0
    sho_error = 0
    for rec in recent:
        subs = rec.get("subsystems")
        if not isinstance(subs, dict):
            continue
        if subs.get("sho") == "error":
            sho_error += 1
        else:
            sho_ok += 1

    def _count_sho_errors(slice_: list) -> int:
        c = 0
        for r in slice_:
            s = r.get("subsystems")
            if isinstance(s, dict) and s.get("sho") == "error":
                c += 1
        return c

    if len(recent) >= 10:
        first5_err = _count_sho_errors(recent[:5])
        last5_err = _count_sho_errors(recent[-5:])
        if last5_err < first5_err:
            trend = "improving"
        elif last5_err > first5_err:
            trend = "declining"
        else:
            trend = "flat"
    else:
        trend = "flat"

    return {
        "window": n,
        "sho_ok": sho_ok,
        "sho_error": sho_error,
        "trend": trend,
    }


# ------------------------------------------------------------
# Phase 4: system health & readiness indicators
# ------------------------------------------------------------


def compute_system_health(n: int = 50) -> Dict[str, Any]:
    """
    High-level health descriptor derived from error rates, stability, and
    SHO trend.  Purely descriptive — does NOT feed governor logic.

    Classification:
      healthy   – every subsystem < 10 % error rate AND stable
      degraded  – any subsystem 10–30 % OR SHO trend declining
      unhealthy – any subsystem > 30 % OR unstable
    """
    er = compute_error_rate(n)
    rates = er.get("rates") or {}
    stab = compute_stability_signal(n)
    sho = compute_sho_trend(min(n, 20))

    max_rate = max(rates.values()) if rates else 0.0

    if max_rate > 0.30 or not stab.get("stable", True):
        overall = "unhealthy"
    elif max_rate > 0.10 or sho.get("trend") == "declining":
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "window": n,
        "overall": overall,
        "error_rates": rates,
        "stability": stab,
        "sho_trend": sho,
    }


def compute_readiness_level(n: int = 50) -> Dict[str, Any]:
    """
    Cockpit-only readiness level (0–3).  NOT an autonomy signal.

      3 – optimal   (healthy + SHO improving)
      2 – nominal   (healthy or minor issues, stable)
      1 – degraded  (elevated errors or instability)
      0 – critical  (unhealthy)
    """
    health = compute_system_health(n)
    overall = health.get("overall", "unhealthy")
    sho_trend = (health.get("sho_trend") or {}).get("trend", "flat")

    if overall == "unhealthy":
        level, desc = 0, "critical"
    elif overall == "degraded":
        level, desc = 1, "degraded"
    elif sho_trend == "improving":
        level, desc = 3, "optimal"
    else:
        level, desc = 2, "nominal"

    return {"window": n, "level": level, "description": desc}


# ------------------------------------------------------------
# Phase 6: long-running operation metrics
# ------------------------------------------------------------


def compute_cycle_durations(n: int = 50) -> Dict[str, Any]:
    """Duration stats over the last *n* telemetry records."""
    recent = _TELEMETRY_BUFFER[-n:] if n > 0 else []
    durations: List[float] = []
    for rec in recent:
        d = rec.get("duration")
        if isinstance(d, (int, float)):
            durations.append(float(d))

    if durations:
        avg = sum(durations) / len(durations)
        mn = min(durations)
        mx = max(durations)
    else:
        avg = mn = mx = 0.0

    return {
        "window": n,
        "durations": durations,
        "avg": round(avg, 6),
        "min": round(mn, 6),
        "max": round(mx, 6),
    }


def compute_runtime_drift(n: int = 50) -> Dict[str, Any]:
    """
    Descriptive drift classification based on cycle durations.

    Thresholds are purely informational — they do NOT feed governor logic.
      none   – avg < 0.1 s and max < 0.2 s
      mild   – avg < 0.5 s and max < 1.0 s
      severe – otherwise
    """
    stats = compute_cycle_durations(n)
    avg = stats["avg"]
    mx = stats["max"]

    if avg < 0.1 and mx < 0.2:
        drift = "none"
    elif avg < 0.5 and mx < 1.0:
        drift = "mild"
    else:
        drift = "severe"

    return {
        "window": n,
        "drift": drift,
        "avg_duration": avg,
        "max_duration": mx,
    }


# ------------------------------------------------------------
# Phase 7: runtime integrity & degradation detection
# ------------------------------------------------------------


def compute_integrity_flags(n: int = 50) -> Dict[str, Any]:
    """
    Descriptive flags that highlight subtle degradation patterns.

    All flags default to False when fewer than 20 records are available.
    These are observational only — they do NOT feed governor logic.
    """
    recent = _TELEMETRY_BUFFER[-n:] if n > 0 else []

    flags = {
        "increasing_error_rate": False,
        "sho_regression": False,
        "duration_creep": False,
        "stability_loss": False,
    }

    if len(recent) >= 20:
        first10 = recent[:10]
        last10 = recent[-10:]

        def _total_errors(slice_: list) -> int:
            total = 0
            for r in slice_:
                s = r.get("subsystems")
                if not isinstance(s, dict):
                    continue
                for key in _SUBSYSTEM_KEYS:
                    if s.get(key) == "error":
                        total += 1
            return total

        flags["increasing_error_rate"] = _total_errors(last10) > _total_errors(first10)

        sho = compute_sho_trend(min(n, 20))
        flags["sho_regression"] = sho.get("trend") == "declining"

        def _avg_dur(slice_: list) -> float:
            durs = [
                float(r["duration"])
                for r in slice_
                if isinstance(r.get("duration"), (int, float))
            ]
            return (sum(durs) / len(durs)) if durs else 0.0

        avg_first = _avg_dur(first10)
        avg_last = _avg_dur(last10)
        if avg_first > 0:
            flags["duration_creep"] = (avg_last - avg_first) / avg_first > 0.20
        else:
            flags["duration_creep"] = avg_last > 0

        stab = compute_stability_signal(n)
        flags["stability_loss"] = not stab.get("stable", True)

    return {"window": n, "flags": flags}


def compute_degradation_level(n: int = 50) -> Dict[str, Any]:
    """
    Aggregate degradation level derived from integrity flags.

    Purely descriptive — NOT an autonomy signal.
      0 / none  – zero flags active
      1 / minor – exactly one flag active
      2 / major – two or more flags active
    """
    integrity = compute_integrity_flags(n)
    active = sum(1 for v in integrity["flags"].values() if v)

    if active >= 2:
        level, desc = 2, "major"
    elif active == 1:
        level, desc = 1, "minor"
    else:
        level, desc = 0, "none"

    return {
        "window": n,
        "level": level,
        "description": desc,
        "flags": integrity["flags"],
    }


# ------------------------------------------------------------
# Phase 8: maintenance readiness gate
# ------------------------------------------------------------


def compute_maintenance_readiness(n: int = 50) -> Dict[str, Any]:
    """
    Descriptive readiness gate for maintenance operations.

    Composes health, readiness, degradation, and drift into a single
    green/yellow/red classification with human-readable reasons.
    Purely informational — NOT an autonomy signal.
    """
    health = compute_system_health(n)
    readiness = compute_readiness_level(n)
    degradation = compute_degradation_level(n)
    drift = compute_runtime_drift(n)

    overall_health = health.get("overall", "unhealthy")
    rd_level = readiness.get("level", 0)
    deg_level = degradation.get("level", 0)
    drift_class = drift.get("drift", "severe")
    stability_lost = (degradation.get("flags") or {}).get("stability_loss", False)

    reasons: List[str] = []

    # --- red conditions ---
    is_red = False
    if overall_health == "unhealthy":
        reasons.append(f"system health is {overall_health}")
        is_red = True
    if deg_level >= 2:
        reasons.append(f"degradation is major (level {deg_level})")
        is_red = True
    if stability_lost:
        reasons.append("stability_loss flag is active")
        is_red = True

    if is_red:
        return {
            "window": n,
            "ready": False,
            "level": "red",
            "reasons": reasons,
            "health": health,
            "readiness": readiness,
            "degradation": degradation,
            "drift": drift,
        }

    # --- yellow conditions ---
    is_yellow = False
    if overall_health == "degraded":
        reasons.append(f"system health is {overall_health}")
        is_yellow = True
    if deg_level == 1:
        reasons.append(f"degradation is minor (level {deg_level})")
        is_yellow = True
    if drift_class == "severe":
        reasons.append(f"runtime drift is {drift_class}")
        is_yellow = True

    if is_yellow:
        return {
            "window": n,
            "ready": False,
            "level": "yellow",
            "reasons": reasons,
            "health": health,
            "readiness": readiness,
            "degradation": degradation,
            "drift": drift,
        }

    # --- green ---
    if rd_level >= 2 and drift_class in ("none", "mild"):
        reasons.append("all checks passed")
    else:
        if rd_level < 2:
            reasons.append(f"readiness level {rd_level} (want >= 2)")
        if drift_class not in ("none", "mild"):
            reasons.append(f"drift is {drift_class}")

    ready = rd_level >= 2 and drift_class in ("none", "mild")

    return {
        "window": n,
        "ready": ready,
        "level": "green" if ready else "yellow",
        "reasons": reasons,
        "health": health,
        "readiness": readiness,
        "degradation": degradation,
        "drift": drift,
    }


# ------------------------------------------------------------
# Phase 9: pre-maintenance checklist & safety envelope
# ------------------------------------------------------------


def compute_premaintenance_checklist(n: int = 50) -> Dict[str, Any]:
    """
    Structured checklist defining the safety envelope for maintenance.

    Each item is classified ok / warn / fail based on current telemetry.
    Overall: fail if any item fails, caution if any warns, pass otherwise.
    Purely informational — NOT an autonomy signal.
    """
    health = compute_system_health(n)
    stability = compute_stability_signal(n)
    degradation = compute_degradation_level(n)
    drift = compute_runtime_drift(n)
    readiness = compute_readiness_level(n)
    maint_ready = compute_maintenance_readiness(n)

    checklist: List[Dict[str, str]] = []

    # 1. System health
    h = health.get("overall", "unhealthy")
    if h == "healthy":
        checklist.append({"item": "System health within safe envelope", "status": "ok", "details": h})
    elif h == "degraded":
        checklist.append({"item": "System health within safe envelope", "status": "warn", "details": h})
    else:
        checklist.append({"item": "System health within safe envelope", "status": "fail", "details": h})

    # 2. Stability
    stable = stability.get("stable", False)
    if stable:
        checklist.append({"item": "Subsystem stability maintained", "status": "ok", "details": "stable"})
    else:
        checklist.append({"item": "Subsystem stability maintained", "status": "fail", "details": "unstable"})

    # 3. Degradation
    dl = degradation.get("level", 0)
    if dl == 0:
        checklist.append({"item": "No major degradation detected", "status": "ok", "details": "none"})
    elif dl == 1:
        checklist.append({"item": "No major degradation detected", "status": "warn", "details": "minor"})
    else:
        checklist.append({"item": "No major degradation detected", "status": "fail", "details": "major"})

    # 4. Runtime drift
    dc = drift.get("drift", "severe")
    if dc in ("none", "mild"):
        checklist.append({"item": "Runtime drift acceptable", "status": "ok", "details": dc})
    else:
        checklist.append({"item": "Runtime drift acceptable", "status": "warn", "details": dc})

    # 5. Readiness level
    rl = readiness.get("level", 0)
    if rl >= 2:
        checklist.append({"item": "Readiness level sufficient", "status": "ok", "details": f"level {rl}"})
    elif rl == 1:
        checklist.append({"item": "Readiness level sufficient", "status": "warn", "details": f"level {rl}"})
    else:
        checklist.append({"item": "Readiness level sufficient", "status": "fail", "details": f"level {rl}"})

    statuses = [c["status"] for c in checklist]
    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "caution"
    else:
        overall = "pass"

    return {
        "window": n,
        "checklist": checklist,
        "overall": overall,
        "maintenance_readiness": maint_ready,
    }
