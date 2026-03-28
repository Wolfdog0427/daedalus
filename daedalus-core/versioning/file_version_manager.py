# versioning/file_version_manager.py

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, List

from versioning.version_manager import VersionManager, VersionMetadata
from core.contracts import CandidateSummary


class FileVersionManager(VersionManager):
    """
    Concrete VersionManager implementation that stores version metadata
    in a durable JSON index under storage_root.

    This manager:
      - Tracks all versions (LKG + historical)
      - Stores VersionMetadata entries
      - Stores candidate summaries
      - Provides logical rollback (pointer switch)
      - Never mutates or deletes past versions
      - Survives REPL/state/debug resets
    """

    INDEX_FILENAME = "versions_index.json"
    _MAX_VERSIONS = 200
    _MAX_CANDIDATES = 100

    def __init__(self, repo_root: str, storage_root: str):
        super().__init__(repo_root, storage_root)

        self.index_path = os.path.join(self.storage_root, self.INDEX_FILENAME)
        os.makedirs(self.storage_root, exist_ok=True)

        if not os.path.exists(self.index_path):
            self._write_index({
                "versions": [],        # List[VersionMetadata as dict]
                "candidates": [],      # List[CandidateSummary as dict]
                "current_lkg": None,   # version_id
            })

        self.index = self._load_index()

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _load_index(self) -> Dict:
        default = {"versions": [], "candidates": [], "current_lkg": None}
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return default
            data.setdefault("versions", [])
            data.setdefault("candidates", [])
            data.setdefault("current_lkg", None)
            return data
        except (json.JSONDecodeError, OSError, ValueError):
            return default

    def _write_index(self, data: Dict) -> None:
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _save(self) -> None:
        self._write_index(self.index)

    def _new_version_id(self) -> str:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        compact = ts.replace(":", "").replace("-", "").replace(".", "")
        return f"v-{compact}"

    def _new_candidate_id(self) -> str:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        compact = ts.replace(":", "").replace("-", "").replace(".", "")
        return f"c-{compact}"

    # ------------------------------------------------------------
    # VersionManager interface
    # ------------------------------------------------------------

    def snapshot_lkg(self, reason: str) -> str:
        """
        Create a new Last Known Good version snapshot.
        This stores metadata only — it does NOT copy code.
        """
        version_id = self._new_version_id()
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        metadata = VersionMetadata(
            version_id=version_id,
            timestamp=ts,
            reason=reason,
            modules_modified={},          # No assumptions — caller can update later
            drift_net_improvement=0.0,    # No assumptions
            confidence=1.0,               # Default confidence
        )

        self.index["versions"].append(metadata.__dict__)
        if len(self.index["versions"]) > self._MAX_VERSIONS:
            self.index["versions"] = self.index["versions"][-self._MAX_VERSIONS:]
        self.index["current_lkg"] = version_id
        self._save()

        return version_id

    def store_candidate(self, candidate: CandidateSummary) -> str:
        """
        Store a candidate improvement proposal.
        """
        candidate_id = self._new_candidate_id()
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        plan = candidate.plan
        entry = {
            "candidate_id": candidate_id,
            "timestamp": ts,
            "recommendation": candidate.recommendation,
            "best_cycle_index": candidate.best_cycle_index,
            "risks": candidate.risks,
            "change_budget_files": plan.change_budget_files if plan else 0,
            "change_budget_lines": plan.change_budget_lines if plan else 0,
        }

        self.index["candidates"].append(entry)
        if len(self.index["candidates"]) > self._MAX_CANDIDATES:
            self.index["candidates"] = self.index["candidates"][-self._MAX_CANDIDATES:]
        self._save()

        return candidate_id

    def rollback_to(self, version_id: str) -> None:
        """
        Logical rollback: simply point current_lkg to an existing version.
        Does not modify code — orchestrator or external system handles that.
        Raises ValueError if version_id is not known.
        """
        known_ids = {v.get("version_id") for v in self.index.get("versions", [])}
        if version_id not in known_ids:
            raise ValueError(f"Unknown version_id '{version_id}' — cannot rollback")
        self.index["current_lkg"] = version_id
        self._save()

    def get_lkg(self) -> Optional[str]:
        return self.index.get("current_lkg")

    # ------------------------------------------------------------
    # Additional helpers (optional but useful)
    # ------------------------------------------------------------

    def list_versions(self) -> List[VersionMetadata]:
        results = []
        for v in self.index.get("versions", []):
            try:
                results.append(VersionMetadata(**v))
            except (TypeError, KeyError):
                continue
        return results

    def list_candidates(self) -> List[Dict]:
        return self.index.get("candidates", [])

    def pretty_versions(self) -> str:
        versions = self.list_versions()
        current = self.get_lkg()

        if not versions:
            return "No versions recorded."

        lines = ["Known versions:"]
        for v in versions:
            marker = " (LKG)" if v.version_id == current else ""
            lines.append(f"- {v.version_id}{marker}")
            lines.append(f"    ts:     {v.timestamp}")
            lines.append(f"    reason: {v.reason}")
            if v.modules_modified:
                lines.append(f"    modules_modified: {v.modules_modified}")
            lines.append(f"    drift_net_improvement: {v.drift_net_improvement}")
            lines.append(f"    confidence: {v.confidence}")
        return "\n".join(lines)

    def pretty_candidates(self) -> str:
        candidates = self.list_candidates()
        if not candidates:
            return "No candidates recorded."

        lines = ["Recorded candidates:"]
        for c in candidates:
            lines.append(f"- {c.get('candidate_id', '?')}")
            lines.append(f"    ts:             {c.get('timestamp', '?')}")
            lines.append(f"    recommendation: {c.get('recommendation', '?')}")
            lines.append(f"    best_cycle:     {c.get('best_cycle_index', '?')}")
            lines.append(f"    risks:          {c.get('risks', [])}")
            lines.append(f"    budget:         {c.get('change_budget_files', 0)} files, "
                         f"{c.get('change_budget_lines', 0)} lines")
        return "\n".join(lines)
