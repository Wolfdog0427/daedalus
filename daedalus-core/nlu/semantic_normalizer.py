# nlu/semantic_normalizer.py

import re
from typing import Any, Dict, List

class SemanticNormalizer:
    def normalize(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)

        tokens = cleaned.split()

        return {
            "raw": text,
            "cleaned": cleaned,
            "tokens": tokens,
        }
