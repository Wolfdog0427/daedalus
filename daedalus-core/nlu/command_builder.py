# nlu/command_builder.py

from typing import Any, Dict

class CommandBuilder:
    def build(self, classified: Dict[str, Any]) -> Dict[str, Any]:
        intent = classified.get("canonical_intent")
        repaired = classified.get("normalized_text", classified.get("repaired", ""))

        if not intent:
            return {
                "raw": classified.get("raw", ""),
                "intent": "unknown",
                "args": {},
                "repaired": repaired,
                "repair_confidence": 0.5,
            }

        return {
            "raw": classified.get("raw", ""),
            "intent": intent,
            "args": {},
            "repaired": repaired,
            "repair_confidence": 1.0,
        }
