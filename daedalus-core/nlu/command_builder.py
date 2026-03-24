# nlu/command_builder.py

from typing import Dict

class CommandBuilder:
    def build(self, classified: Dict[str, any]) -> Dict[str, any]:
        intent = classified.get("canonical_intent")

        if not intent:
            return {
                "raw": classified["raw"],
                "intent": "unknown",
                "args": {},
                "repaired": classified["cleaned"],
                "repair_confidence": 0.5,
            }

        return {
            "raw": classified["raw"],
            "intent": intent,
            "args": {},  # Phase 2 will add argument extraction
            "repaired": classified["cleaned"],
            "repair_confidence": 1.0,
        }
