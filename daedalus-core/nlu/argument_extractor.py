# nlu/argument_extractor.py

from typing import Dict, Any, Optional

ORDINAL_WORDS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
}

POSITION_WORDS = {
    "top": 1,
    "start": 1,
    "bottom": -1,
    "end": -1,
}

MOVEMENT_WORDS = {
    "up": -1,
    "down": +1,
    "higher": -1,
    "lower": +1,
}

def extract_ordinal(tokens):
    for t in tokens:
        if t in ORDINAL_WORDS:
            return ORDINAL_WORDS[t]
    return None

def extract_position(tokens):
    for t in tokens:
        if t in POSITION_WORDS:
            return POSITION_WORDS[t]
    return None

def extract_movement(tokens):
    for t in tokens:
        if t in MOVEMENT_WORDS:
            return MOVEMENT_WORDS[t]
    return None

def extract_arguments(nlu: Dict[str, Any]) -> Dict[str, Any]:
    tokens = nlu.get("tokens", [])

    return {
        "ordinal": extract_ordinal(tokens),
        "position": extract_position(tokens),
        "movement": extract_movement(tokens),
    }
