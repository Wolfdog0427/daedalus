import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict, List

from core.contracts import SecurityEvent, SecurityStatus


INTEGRITY_INDEX_FILENAME = ".integrity_index.json"


@dataclass
class FileIntegrityRecord:
    path: str
    hash: str
    last_known_source: str   # "orchestrator" | "user" | "external"
    last_change_reason: str  # link to candidate id / note


class CodeIntegrity:
    def __init__(self, repo_root: str, storage_root: str):
        self.repo_root = repo_root
        self.storage_root = storage_root
        self.index_path = os.path.join(storage_root, INTEGRITY_INDEX_FILENAME)
        self.records: Dict[str, FileIntegrityRecord] = {}
        self._load_index()

    def snapshot_integrity(self, source: str, reason: str, tracked_files: List[str]) -> None:
        for rel_path in tracked_files:
            abs_path = os.path.join(self.repo_root, rel_path)
            file_hash = self._hash_file(abs_path)
            self.records[rel_path] = FileIntegrityRecord(
                path=rel_path,
                hash=file_hash,
                last_known_source=source,
                last_change_reason=reason,
            )
        self._save_index()

    def verify_integrity(self, tracked_files: List[str]) -> SecurityStatus:
        events: List[SecurityEvent] = []
        integrity_ok = True
        unknown_capabilities_detected = False  # to be set by higher layers

        for rel_path in tracked_files:
            abs_path = os.path.join(self.repo_root, rel_path)
            current_hash = self._hash_file(abs_path)

            record = self.records.get(rel_path)
            if record is None:
                integrity_ok = False
                events.append(SecurityEvent(
                    timestamp=self._now(),
                    event_type="untracked_change",
                    severity="high",
                    details={"message": "File not in integrity index", "path": rel_path},
                    affected_files=[rel_path],
                ))
                continue

            if current_hash != record.hash:
                integrity_ok = False
                events.append(SecurityEvent(
                    timestamp=self._now(),
                    event_type="integrity_mismatch",
                    severity="critical",
                    details={
                        "message": "Hash mismatch",
                        "path": rel_path,
                        "last_known_source": record.last_known_source,
                        "last_change_reason": record.last_change_reason,
                    },
                    affected_files=[rel_path],
                ))

        mode = "normal" if integrity_ok else "suspicious"

        return SecurityStatus(
            mode=mode,
            last_events=events,
            integrity_ok=integrity_ok,
            unknown_capabilities_detected=unknown_capabilities_detected,
            recommendations=self._recommendations_from_events(events),
        )

    def _hash_file(self, path: str) -> str:
        if not os.path.exists(path):
            return "<missing>"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _load_index(self) -> None:
        if not os.path.exists(self.index_path):
            self.records = {}
            return
        with open(self.index_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.records = {
            path: FileIntegrityRecord(**rec)
            for path, rec in raw.items()
        }

    def _save_index(self) -> None:
        raw = {
            path: {
                "path": rec.path,
                "hash": rec.hash,
                "last_known_source": rec.last_known_source,
                "last_change_reason": rec.last_change_reason,
            }
            for path, rec in self.records.items()
        }
        os.makedirs(self.storage_root, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, sort_keys=True)

    def _now(self) -> str:
        import time
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

    def _recommendations_from_events(self, events: List[SecurityEvent]) -> List[str]:
        if not events:
            return []
        return [
            "Review integrity events and compare diffs for affected files.",
            "Consider restoring Last Known Good snapshot if changes are not trusted.",
        ]
