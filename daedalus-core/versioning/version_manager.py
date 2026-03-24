from dataclasses import dataclass
from typing import Dict, Optional

from core.contracts import CandidateSummary


@dataclass
class VersionMetadata:
    version_id: str
    timestamp: str
    reason: str
    modules_modified: Dict[str, int]
    drift_net_improvement: float
    confidence: float


class VersionManager:
    def __init__(self, repo_root: str, storage_root: str):
        self.repo_root = repo_root
        self.storage_root = storage_root
        # TODO: load existing metadata index

    def snapshot_lkg(self, reason: str) -> str:
        """Create a Last Known Good snapshot and return its version_id."""
        raise NotImplementedError

    def store_candidate(self, candidate: CandidateSummary) -> str:
        """Store a candidate version (after human approval)."""
        raise NotImplementedError

    def rollback_to(self, version_id: str) -> None:
        """Restore codebase to a previous version."""
        raise NotImplementedError

    def get_lkg(self) -> Optional[str]:
        """Return the current Last Known Good version_id."""
        raise NotImplementedError
