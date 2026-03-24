from dataclasses import dataclass
from typing import List


@dataclass
class ReorgAction:
    action_type: str          # "move" | "split" | "merge" | "rename" | "create_dir"
    source: str
    target: str
    details: dict


@dataclass
class ReorganizationPlan:
    actions: List[ReorgAction]
    rationale: str
