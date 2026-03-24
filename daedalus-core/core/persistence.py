"""
Persistence layer for goals and state.

Stores:
- goals
- conversation state

in a simple JSON file.
"""

import json
from typing import Dict, Any


class PersistenceManager:
    def __init__(self, path: str = "assistant_state.json"):
        self.path = path

    def save(self, state: Dict[str, Any], goals: Dict[str, Any]) -> None:
        data = {
            "state": state,
            "goals": goals,
        }
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silent failure; persistence is best-effort
            pass

    def load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "state": data.get("state", {}),
                "goals": data.get("goals", {}),
            }
        except Exception:
            return {"state": {}, "goals": {}}
