# versioning/file_version_manager.py

import json
import os
from datetime import datetime
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
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"versions": [], "candidates": [], "current_lkg": None}

    def _write_index(self, data: Dict) -> None:
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Never break the system due to version index write failure
            pass

    def _save(self) -> None:
        self._write_index(self.index)

    def _new_version_id(self) -> str:
        ts = datetime.utcnow().isoformat() + "Z"
        compact = ts.replace(":", "").replace("-", "").replace(".", "")
        return f"v-{compact}"

    def _new_candidate_id(self) -> str:
        ts = datetime.utcnow().isoformat() + "Z"
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
        ts = datetime.utcnow().isoformat() + "Z"

        metadata = VersionMetadata(
            version_id=version_id,
            timestamp=ts,
            reason=reason,
            modules_modified={},          # No assumptions — caller can update later
            drift_net_improvement=0.0,    # No assumptions
            confidence=1.0,               # Default confidence
        )

        # Store as dict
        self.index["versions"].append(metadata.__dict__)
        self.index["current_lkg"] = version_id
        self._save()

        return version_id

    def store_candidate(self, candidate: CandidateSummary) -> str:
        """
        Store a candidate improvement proposal.
        """
        candidate_id = self._new_candidate_id()
        ts = datetime.utcnow().isoformat() + "Z"

        entry = {
            "candidate_id": candidate_id,
            "timestamp": ts,
            "proposal_type": candidate.proposal_type,
            "description": candidate.description,
            "expected_benefit": candidate.expected_benefit,
            "change_budget_files": candidate.change_budget_files,
            "change_budget_lines": candidate.change_budget_lines,
        }

        self.index["candidates"].append(entry)
        self._save()

        return candidate_id

    def rollback_to(self, version_id: str) -> None:
        """
        Logical rollback: simply point current_lkg to an existing version.
        Does not modify code — orchestrator or external system handles that.
        """
        known_ids = {v["version_id"] for v in self.index["versions"]}
        if version_id in known_ids:
            self.index["current_lkg"] = version_id
            self._save()
        # If unknown, silently ignore (safe behavior)

    def get_lkg(self) -> Optional[str]:
        return self.index.get("current_lkg")

    # ------------------------------------------------------------
    # Additional helpers (optional but useful)
    # ------------------------------------------------------------

    def list_versions(self) -> List[VersionMetadata]:
        return [
            VersionMetadata(**v)
            for v in self.index.get("versions", [])
        ]

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
            lines.append(f"- {c['candidate_id']}")
            lines.append(f"    ts:   {c['timestamp']}")
            lines.append(f"    type: {c['proposal_type']}")
            lines.append(f"    desc: {c['description']}")
            lines.append(f"    expected_benefit: {c['expected_benefit']}")
            lines.append(f"    budget: {c['change_budget_files']} files, {c['change_budget_lines']} lines")
        return "\n".join(lines)
