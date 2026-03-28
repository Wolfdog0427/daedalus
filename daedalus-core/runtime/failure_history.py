# runtime/failure_history.py

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class FailureHistory:
    """
    Lightweight persistent failure history store + pattern aggregator.

    Stores one JSON object per line (JSONL) with:
      - timestamp
      - snapshot metadata
      - failure report summary
      - proposal summary
      - plan summary
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._file_lock = threading.Lock()
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # ------------------------------------------------------------
    # RECORDING
    # ------------------------------------------------------------

    def record(
        self,
        snapshot: Dict[str, Any],
        failure_report: Optional[Any] = None,
        proposal: Optional[Any] = None,
        plan: Optional[Any] = None,
    ) -> None:
        """
        Append a single failure interaction to the history log.
        Best-effort: never raises.
        """
        try:
            entry: Dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "error_type": snapshot.get("error_type"),
                "error_message": snapshot.get("error_message"),
                "subsystem": snapshot.get("subsystem"),
                "pipeline_stage": snapshot.get("pipeline_stage"),
                "user_input": snapshot.get("user_input"),
                "parsed_intent": snapshot.get("parsed_intent"),
                "resolver_target": snapshot.get("resolver_target"),
                "state_changed": snapshot.get("state_changed"),
                "changed_keys": snapshot.get("changed_keys"),
                "hostility_score": snapshot.get("hostility_score"),
            }

            if failure_report is not None:
                entry["failure_report"] = {
                    "failure_type": getattr(failure_report, "failure_type", None),
                    "details": getattr(failure_report, "details", None),
                }

            if proposal is not None:
                entry["proposal"] = {
                    "description": getattr(proposal, "description", None),
                    "proposal_type": getattr(proposal, "proposal_type", None),
                    "expected_benefit": getattr(proposal, "expected_benefit", None),
                }

            if plan is not None:
                entry["plan"] = {
                    "change_budget_files": getattr(plan, "change_budget_files", None),
                    "change_budget_lines": getattr(plan, "change_budget_lines", None),
                }

            with self._file_lock:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            # Never break the system because of logging issues
            pass

    # ------------------------------------------------------------
    # LOADING
    # ------------------------------------------------------------

    def _load_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        entries: List[Dict[str, Any]] = []
        try:
            with self._file_lock, open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError:
            return []
        return entries

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        entries = self._load_all()
        return entries[-limit:] if limit > 0 else entries

    # ------------------------------------------------------------
    # PATTERN AGGREGATION
    # ------------------------------------------------------------

    def summarize_patterns(self) -> Dict[str, Any]:
        """
        Aggregate failures by type, subsystem, and pipeline stage.
        """
        entries = self._load_all()
        by_failure: Dict[str, int] = {}
        by_subsystem: Dict[str, int] = {}
        by_stage: Dict[str, int] = {}

        for e in entries:
            ft = e.get("error_type") or "unknown"
            ss = e.get("subsystem") or "unknown"
            st = e.get("pipeline_stage") or "unknown"

            by_failure[ft] = by_failure.get(ft, 0) + 1
            by_subsystem[ss] = by_subsystem.get(ss, 0) + 1
            by_stage[st] = by_stage.get(st, 0) + 1

        return {
            "total": len(entries),
            "by_failure": by_failure,
            "by_subsystem": by_subsystem,
            "by_stage": by_stage,
        }

    # ------------------------------------------------------------
    # PRETTY PRINTERS
    # ------------------------------------------------------------

    def pretty_recent(self, limit: int = 20) -> str:
        entries = self.recent(limit)
        if not entries:
            return "No failures recorded."

        lines: List[str] = []
        lines.append(f"Recent failures (last {len(entries)}):")
        for e in entries:
            ts = e.get("ts", "?")
            et = e.get("error_type", "unknown")
            ss = e.get("subsystem", "unknown")
            st = e.get("pipeline_stage", "unknown")
            ui = e.get("user_input", "")
            fm = e.get("error_message", "")
            lines.append(f"- [{ts}] {et} @ {ss}/{st}")
            if ui:
                lines.append(f"    input: {ui}")
            if fm:
                lines.append(f"    msg:   {fm}")
        return "\n".join(lines)

    def pretty_patterns(self) -> str:
        summary = self.summarize_patterns()
        total = summary.get("total", 0)
        if total == 0:
            return "No failure patterns yet."

        lines: List[str] = []
        lines.append(f"Failure patterns (total {total} recorded):")
        lines.append("")
        lines.append("By failure type:")
        for k, v in sorted(summary["by_failure"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {k}: {v}")

        lines.append("")
        lines.append("By subsystem:")
        for k, v in sorted(summary["by_subsystem"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {k}: {v}")

        lines.append("")
        lines.append("By pipeline stage:")
        for k, v in sorted(summary["by_stage"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {k}: {v}")

        return "\n".join(lines)
