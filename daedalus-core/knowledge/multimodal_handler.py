# knowledge/multimodal_handler.py

"""
Multi-Modal Knowledge Handler

Extends the KB to handle structured data (tables, JSON, CSV),
code snippets, and image references alongside text. Each modality
gets appropriate processing and validation.

Architecture fit:
- Hooks into batch_ingestion for content classification
- Normalizes all modalities to graph-compatible text for entity extraction
- Modality-specific validation (syntax check for code, schema for structured)
- Existing text items classified as content_type="text" automatically

All items without modality metadata are treated as plain text —
no existing behavior changes.
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional

# Content type constants
CONTENT_TEXT = "text"
CONTENT_STRUCTURED = "structured"
CONTENT_CODE = "code"
CONTENT_IMAGE_REF = "image_ref"
CONTENT_MIXED = "mixed"

# Code language detection patterns
_CODE_PATTERNS = {
    "python": re.compile(r'(?:def |class |import |from .+ import |if __name__)'),
    "javascript": re.compile(r'(?:function |const |let |var |=>|require\()'),
    "sql": re.compile(r'(?:SELECT |INSERT |UPDATE |DELETE |CREATE TABLE)', re.IGNORECASE),
    "json": re.compile(r'^\s*[\[{]'),
    "yaml": re.compile(r'^[\w_]+:\s', re.MULTILINE),
}

# Structured data patterns
_TABLE_PATTERN = re.compile(r'(?:\|[^|]+\|){2,}')
_CSV_PATTERN = re.compile(r'^[^,]+(?:,[^,]+){2,}$', re.MULTILINE)
_JSON_PATTERN = re.compile(r'^\s*[\[{].*[\]}]\s*$', re.DOTALL)


# ------------------------------------------------------------
# CONTENT CLASSIFICATION
# ------------------------------------------------------------

def classify_content_type(text: str, source: str = "") -> str:
    """
    Detect whether input is text, structured data, code, or image reference.
    Returns one of the CONTENT_* constants.
    """
    if not text.strip():
        return CONTENT_TEXT

    stripped = text.strip()

    if _is_image_reference(stripped, source):
        return CONTENT_IMAGE_REF

    if _is_json(stripped):
        return CONTENT_STRUCTURED

    code_score = _code_likelihood(stripped)
    struct_score = _structured_likelihood(stripped)

    if code_score > 0.6:
        return CONTENT_CODE
    if struct_score > 0.6:
        return CONTENT_STRUCTURED
    if code_score > 0.3 and struct_score > 0.3:
        return CONTENT_MIXED

    return CONTENT_TEXT


def _is_image_reference(text: str, source: str) -> bool:
    """Check for image file references or URLs."""
    image_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")
    for ext in image_exts:
        if text.lower().endswith(ext) or ext in source.lower():
            return True
    return bool(re.match(r'https?://.*\.(png|jpg|jpeg|gif|webp|svg)', text, re.IGNORECASE))


def _is_json(text: str) -> bool:
    """Quick check for valid JSON."""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _code_likelihood(text: str) -> float:
    """Score how likely the text is code."""
    score = 0.0
    for lang, pattern in _CODE_PATTERNS.items():
        if pattern.search(text):
            score += 0.3

    indent_lines = sum(1 for line in text.split("\n") if line.startswith("    ") or line.startswith("\t"))
    total_lines = max(1, len(text.split("\n")))
    if indent_lines / total_lines > 0.3:
        score += 0.2

    if text.count("{") > 2 and text.count("}") > 2:
        score += 0.1
    if text.count("(") > 3 and text.count(")") > 3:
        score += 0.1

    return min(1.0, score)


def _structured_likelihood(text: str) -> float:
    """Score how likely the text is structured data."""
    score = 0.0

    if _TABLE_PATTERN.search(text):
        score += 0.5
    if _CSV_PATTERN.search(text):
        score += 0.4
    if _JSON_PATTERN.search(text):
        score += 0.6

    return min(1.0, score)


# ------------------------------------------------------------
# STRUCTURED DATA EXTRACTION
# ------------------------------------------------------------

def extract_structured_data(text: str) -> Dict[str, Any]:
    """
    Parse tables, JSON, CSV into normalized form.
    Returns a dict with the extracted structure and metadata.
    """
    content_type = classify_content_type(text)

    if content_type == CONTENT_STRUCTURED:
        if _is_json(text.strip()):
            try:
                data = json.loads(text.strip())
                return {
                    "format": "json",
                    "data": data,
                    "row_count": len(data) if isinstance(data, list) else 1,
                    "fields": list(data.keys()) if isinstance(data, dict) else [],
                }
            except Exception:
                pass

        if _TABLE_PATTERN.search(text):
            rows = [
                [cell.strip() for cell in line.split("|") if cell.strip()]
                for line in text.split("\n")
                if "|" in line and not line.strip().startswith("|-")
            ]
            return {
                "format": "table",
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(rows[0]) if rows else 0,
            }

        if _CSV_PATTERN.search(text):
            rows = [line.split(",") for line in text.strip().split("\n")]
            return {
                "format": "csv",
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(rows[0]) if rows else 0,
            }

    return {"format": "text", "data": text}


# ------------------------------------------------------------
# NORMALIZATION FOR GRAPH
# ------------------------------------------------------------

def normalize_for_graph(content: str, content_type: str) -> str:
    """
    Convert any modality to a graph-compatible text representation.
    The knowledge graph operates on text — this bridge ensures
    entities can be extracted from any content type.
    """
    if content_type == CONTENT_TEXT:
        return content

    if content_type == CONTENT_CODE:
        return _normalize_code(content)

    if content_type == CONTENT_STRUCTURED:
        return _normalize_structured(content)

    if content_type == CONTENT_IMAGE_REF:
        return f"Image reference: {content[:200]}"

    if content_type == CONTENT_MIXED:
        return content

    return content


def _normalize_code(code: str) -> str:
    """Extract semantic content from code for graph indexing."""
    lines = code.split("\n")
    meaningful = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            meaningful.append(stripped.lstrip("#/ "))
        elif stripped.startswith("def ") or stripped.startswith("class "):
            meaningful.append(stripped)
        elif stripped.startswith("function ") or stripped.startswith("export "):
            meaningful.append(stripped)

    if meaningful:
        return "Code: " + ". ".join(meaningful[:20])
    return f"Code snippet ({len(lines)} lines)"


def _normalize_structured(data_text: str) -> str:
    """Extract semantic content from structured data."""
    extracted = extract_structured_data(data_text)
    fmt = extracted.get("format", "unknown")

    if fmt == "json" and isinstance(extracted.get("data"), dict):
        keys = list(extracted["data"].keys())[:10]
        return f"Structured data with fields: {', '.join(keys)}"

    if fmt in ("table", "csv"):
        rows = extracted.get("rows", [])
        if rows:
            header = ", ".join(str(c) for c in rows[0][:5])
            return f"Table with {extracted.get('row_count', 0)} rows. Headers: {header}"

    return f"Structured data ({fmt})"


# ------------------------------------------------------------
# MODALITY VALIDATION
# ------------------------------------------------------------

def validate_modality(content: str, content_type: str) -> Dict[str, Any]:
    """
    Modality-specific validation.
    Returns a dict with passed/failed and any issues found.
    """
    if content_type == CONTENT_TEXT:
        return {"passed": True, "content_type": content_type}

    if content_type == CONTENT_CODE:
        issues = []
        if len(content) > 100000:
            issues.append("code_too_large")
        if content.count("\n") > 5000:
            issues.append("too_many_lines")
        return {
            "passed": len(issues) == 0,
            "content_type": content_type,
            "issues": issues,
        }

    if content_type == CONTENT_STRUCTURED:
        try:
            extracted = extract_structured_data(content)
            return {
                "passed": True,
                "content_type": content_type,
                "format": extracted.get("format"),
            }
        except Exception as exc:
            return {
                "passed": False,
                "content_type": content_type,
                "issues": [f"parse_error: {exc}"],
            }

    if content_type == CONTENT_IMAGE_REF:
        has_ref = bool(re.search(r'https?://|/[\w/]+\.\w+', content))
        return {
            "passed": has_ref,
            "content_type": content_type,
            "issues": [] if has_ref else ["no_valid_reference"],
        }

    return {"passed": True, "content_type": content_type}


# ------------------------------------------------------------
# METADATA ENRICHMENT
# ------------------------------------------------------------

def enrich_metadata(text: str, content_type: str) -> Dict[str, Any]:
    """Extract modality-specific metadata for storage."""
    meta: Dict[str, Any] = {"content_type": content_type}

    if content_type == CONTENT_CODE:
        for lang, pattern in _CODE_PATTERNS.items():
            if pattern.search(text):
                meta["language"] = lang
                break
        meta["line_count"] = text.count("\n") + 1

    elif content_type == CONTENT_STRUCTURED:
        extracted = extract_structured_data(text)
        meta["structured_format"] = extracted.get("format", "unknown")
        meta["row_count"] = extracted.get("row_count", 0)

    elif content_type == CONTENT_IMAGE_REF:
        urls = re.findall(r'https?://\S+', text)
        if urls:
            meta["image_url"] = urls[0]

    return meta
