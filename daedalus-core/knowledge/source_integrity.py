# knowledge/source_integrity.py

"""
Source Integrity

Hardened validation layer that protects the knowledge base against:
- Misinformation masquerading as trusted sources
- URL spoofing (homoglyph attacks, subdomain tricks, redirect chains)
- Poisoned documents (statistical anomalies, injection payloads,
  coordinated manipulation)
- Source impersonation (claiming to be .edu/.gov when not)
- Content tampering (hash mismatch, unexpected encoding)

Design:
- Sits between external content and the trust scoring system
- Every source claim is validated before trust is assigned
- Integrates with existing systems:
  * WebPolicy (web/policy.py) for domain allow/block
  * InputGateway (runtime/input_gateway.py) for hostile pattern detection
  * WebClient (web/client.py) for content hashing
  * HEM (hem/) for hostile engagement boundaries
  * trust_scoring.py for the actual trust computation
  * batch_ingestion.py source trust registry

Threat model:
- An attacker crafts a URL that looks like a trusted domain
- An attacker poisons a document that passes basic quality checks
- An attacker floods the knowledge base with subtly wrong information
  from a "trusted" source that has been compromised
- An attacker uses encoding tricks to bypass content filtering

Every validation returns a structured IntegrityReport that feeds
into trust scoring as a penalty or gate.
"""

from __future__ import annotations

import re
import hashlib
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse
from collections import Counter

# Cross-system integrations (defensive imports)
try:
    from web.policy import WebPolicy
    from config.web_config import WEB_POLICY
    _WEB_POLICY_AVAILABLE = True
except ImportError:
    _WEB_POLICY_AVAILABLE = False

try:
    from runtime.input_gateway import InputGateway
    _INPUT_GATEWAY_AVAILABLE = True
except ImportError:
    _INPUT_GATEWAY_AVAILABLE = False

try:
    from hem.hem_state_machine import (
        hem_maybe_enter,
        hem_transition_to_postcheck,
        hem_run_post_engagement_checks,
    )
    _HEM_AVAILABLE = True
except ImportError:
    _HEM_AVAILABLE = False


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

HOMOGLYPH_MAP: Dict[str, List[str]] = {
    "a": ["\u0430", "\u00e0", "\u00e1", "\u0101"],  # Cyrillic а, accented
    "e": ["\u0435", "\u00e8", "\u00e9", "\u0113"],
    "o": ["\u043e", "\u00f2", "\u00f3", "\u014d", "\u0030"],  # zero
    "i": ["\u0456", "\u00ec", "\u00ed", "\u012b", "\u006c", "\u0031"],  # l, 1
    "l": ["\u006c", "\u0031", "\u007c", "\u0049"],  # 1, |, I
    "c": ["\u0441", "\u00e7"],
    "p": ["\u0440"],
    "s": ["\u0455"],
    "d": ["\u0501"],
    "g": ["\u0261"],
    "n": ["\u0578"],
    "t": ["\u0442"],
    "u": ["\u0446"],
    "w": ["\u0461"],
}

TRUSTED_DOMAIN_FINGERPRINTS: Dict[str, str] = {
    "wikipedia.org": "wikipedia.org",
    "mit.edu": "mit.edu",
    "stanford.edu": "stanford.edu",
    "arxiv.org": "arxiv.org",
    "nature.com": "nature.com",
    "science.org": "science.org",
    "nih.gov": "nih.gov",
    "nasa.gov": "nasa.gov",
}

SUSPICIOUS_TLD_PATTERNS = [
    r".*\.tk$",
    r".*\.ml$",
    r".*\.ga$",
    r".*\.cf$",
    r".*\.gq$",
    r".*\.xyz$",
    r".*\.top$",
    r".*\.buzz$",
    r".*\.club$",
    r".*\.work$",
]

MAX_SUBDOMAIN_DEPTH = 4
MAX_URL_LENGTH = 2048


# ------------------------------------------------------------
# INTEGRITY REPORT
# ------------------------------------------------------------

def _empty_report(source: str) -> Dict[str, Any]:
    return {
        "source": source,
        "timestamp": time.time(),
        "passed": True,
        "threat_level": "none",
        "flags": [],
        "penalties": [],
        "trust_modifier": 0.0,
        "blocked": False,
    }


def _flag(report: Dict[str, Any], flag: str, penalty: float, severity: str = "warning") -> None:
    report["flags"].append({"flag": flag, "severity": severity})
    report["penalties"].append({"flag": flag, "penalty": penalty})
    report["trust_modifier"] -= penalty

    severity_rank = {"info": 0, "warning": 1, "high": 2, "critical": 3}
    current = severity_rank.get(report["threat_level"], 0)
    new = severity_rank.get(severity, 0)
    if new > current:
        report["threat_level"] = severity

    if severity == "critical":
        report["blocked"] = True
        report["passed"] = False


# ------------------------------------------------------------
# URL VALIDATION
# ------------------------------------------------------------

def validate_url(url: str) -> Dict[str, Any]:
    """
    Comprehensive URL validation against spoofing attacks.
    Integrates with WebPolicy for domain allow/block enforcement.
    """
    report = _empty_report(url)

    if not url or not isinstance(url, str):
        _flag(report, "empty_or_invalid_url", 1.0, "critical")
        return report

    if len(url) > MAX_URL_LENGTH:
        _flag(report, "url_too_long", 0.3, "warning")

    # Check against WebPolicy domain lists
    if _WEB_POLICY_AVAILABLE:
        if not WEB_POLICY.is_domain_allowed(url):
            _flag(report, "web_policy_blocked", 1.0, "critical")

    try:
        parsed = urlparse(url)
    except Exception:
        _flag(report, "url_parse_failure", 1.0, "critical")
        return report

    host = (parsed.hostname or "").lower()
    scheme = parsed.scheme.lower()

    # Scheme validation
    if scheme not in ("https", "http"):
        _flag(report, "non_http_scheme", 0.5, "high")

    if scheme == "http":
        _flag(report, "insecure_http", 0.2, "warning")

    # Homoglyph detection
    homoglyph_hits = _detect_homoglyphs(host)
    if homoglyph_hits:
        _flag(report, f"homoglyph_attack:{','.join(homoglyph_hits)}", 0.8, "critical")

    # Subdomain depth
    parts = host.split(".")
    if len(parts) > MAX_SUBDOMAIN_DEPTH:
        _flag(report, "excessive_subdomain_depth", 0.3, "warning")

    # Trusted domain impersonation
    impersonation = _detect_domain_impersonation(host)
    if impersonation:
        _flag(report, f"domain_impersonation:{impersonation}", 0.9, "critical")

    # Suspicious TLD
    for pattern in SUSPICIOUS_TLD_PATTERNS:
        if re.match(pattern, host):
            _flag(report, f"suspicious_tld:{host}", 0.3, "warning")
            break

    # IP address as hostname
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        _flag(report, "ip_address_hostname", 0.4, "high")

    # Embedded credentials
    if parsed.username or parsed.password:
        _flag(report, "embedded_credentials", 0.6, "high")

    # Port tricks
    if parsed.port and parsed.port not in (80, 443, 8080, 8443):
        _flag(report, f"unusual_port:{parsed.port}", 0.2, "warning")

    # Encoded characters in host
    if "%" in host:
        _flag(report, "percent_encoded_hostname", 0.5, "high")

    return report


def _detect_homoglyphs(host: str) -> List[str]:
    """Detect homoglyph characters in a hostname."""
    hits = []
    for char in host:
        for latin, lookalikes in HOMOGLYPH_MAP.items():
            if char in lookalikes:
                hits.append(f"{char}->looks_like_{latin}")
    return hits


def _detect_domain_impersonation(host: str) -> Optional[str]:
    """
    Detect if a domain is trying to impersonate a trusted domain.
    Examples:
    - wikipedia.org.evil.com (trusted domain as subdomain)
    - w1kipedia.org (character substitution)
    - mit-edu.com (TLD in domain name)
    """
    for trusted in TRUSTED_DOMAIN_FINGERPRINTS:
        # Exact match is fine
        if host == trusted or host.endswith(f".{trusted}"):
            continue

        # Trusted domain appears as a subdomain of something else
        if trusted.replace(".", "-") in host:
            return trusted

        # Levenshtein-like: trusted domain minus one char
        trusted_base = trusted.split(".")[0]
        host_base = host.split(".")[0]
        if len(host_base) >= len(trusted_base) - 1:
            common = sum(1 for a, b in zip(trusted_base, host_base) if a == b)
            if common >= len(trusted_base) - 2 and host != trusted:
                if host_base != trusted_base:
                    return trusted

    # .edu/.gov impersonation check
    if not host.endswith(".edu") and not host.endswith(".gov"):
        if ".edu." in host or ".gov." in host:
            return "edu_gov_impersonation"
        if "-edu." in host or "-gov." in host:
            return "edu_gov_impersonation"

    return None


# ------------------------------------------------------------
# CONTENT INTEGRITY
# ------------------------------------------------------------

def validate_content(text: str, source: str = "") -> Dict[str, Any]:
    """
    Validate content for poisoning indicators:
    - Injection payloads hidden in natural text
    - Statistical anomalies suggesting machine-generated spam
    - Encoding manipulation
    - Coordinated misinformation patterns

    Integrates with InputGateway for hostile pattern detection
    and HEM for hostile engagement boundaries.
    """
    report = _empty_report(source)

    if not text or not text.strip():
        _flag(report, "empty_content", 0.5, "warning")
        return report

    # Enter HEM if available (wraps risky content validation)
    if _HEM_AVAILABLE:
        try:
            hem_maybe_enter(
                trigger_reason="source_integrity_content_validation",
                metadata={"source": source, "text_length": len(text)},
            )
        except Exception:
            pass

    # Cross-check with InputGateway hostile pattern detection
    if _INPUT_GATEWAY_AVAILABLE:
        try:
            _, gw_report, hostility_score = InputGateway.sanitize(text[:2000])
            if hostility_score >= 3:
                _flag(report, "input_gateway_hostile", 0.5, "high")
            for pattern in gw_report.get("matched_patterns", []):
                _flag(report, f"gateway:{pattern}", 0.3, "warning")
        except Exception:
            pass

    # Hidden injection payloads
    injection_flags = _detect_content_injection(text)
    for flag_name, severity in injection_flags:
        _flag(report, flag_name, 0.4, severity)

    # Encoding anomalies
    encoding_flags = _detect_encoding_anomalies(text)
    for flag_name in encoding_flags:
        _flag(report, flag_name, 0.3, "warning")

    # Repetition spam
    if _is_repetition_spam(text):
        _flag(report, "repetition_spam", 0.6, "high")

    # Extremely low information density
    info_density = _compute_information_density(text)
    if info_density < 0.1:
        _flag(report, "extremely_low_information_density", 0.4, "warning")

    # Contradiction seeding (text that contradicts itself)
    if _has_internal_contradiction(text):
        _flag(report, "internal_contradiction", 0.3, "warning")

    # HEM phase transition + post-engagement checks
    if _HEM_AVAILABLE:
        try:
            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
        except Exception:
            pass

    return report


def _detect_content_injection(text: str) -> List[tuple]:
    """Detect payloads hidden in text content."""
    flags = []

    injection_patterns = [
        (r"<script\b", "script_injection", "critical"),
        (r"javascript:", "javascript_uri", "critical"),
        (r"data:text/html", "data_uri_injection", "critical"),
        (r"\beval\s*\(", "eval_injection", "high"),
        (r"\bexec\s*\(", "exec_injection", "high"),
        (r"__import__\s*\(", "python_import_injection", "critical"),
        (r"\bSELECT\b.*\bFROM\b.*\bWHERE\b", "sql_injection_pattern", "high"),
        (r";\s*DROP\s+TABLE", "sql_drop_injection", "critical"),
        (r"\{\{.*\}\}", "template_injection", "warning"),
        (r"\\x[0-9a-f]{2}", "hex_escape_sequence", "warning"),
    ]

    for pattern, name, severity in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            flags.append((f"injection:{name}", severity))

    return flags


def _detect_encoding_anomalies(text: str) -> List[str]:
    """Detect encoding-based manipulation."""
    flags = []

    # Zero-width characters (can hide information)
    zero_width = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}
    zw_count = sum(1 for c in text if c in zero_width)
    if zw_count > 0:
        flags.append(f"zero_width_chars:{zw_count}")

    # Right-to-left override (text direction manipulation)
    if "\u202e" in text or "\u200f" in text:
        flags.append("rtl_override_character")

    # Unusual Unicode categories
    unusual = sum(1 for c in text if ord(c) > 0xFFFF)
    if unusual > len(text) * 0.1:
        flags.append("high_ratio_unusual_unicode")

    # Mixed scripts (Latin + Cyrillic in same text block)
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", text))
    if has_latin and has_cyrillic:
        flags.append("mixed_latin_cyrillic")

    return flags


def _is_repetition_spam(text: str) -> bool:
    """Detect repetitive content designed to manipulate frequency metrics."""
    words = text.lower().split()
    if len(words) < 10:
        return False
    counter = Counter(words)
    most_common_count = counter.most_common(1)[0][1]
    return most_common_count > len(words) * 0.3


def _compute_information_density(text: str) -> float:
    """
    Estimate information density. Low density suggests padding/spam.
    Based on unique token ratio.
    """
    words = text.lower().split()
    if not words:
        return 0.0
    unique = len(set(words))
    return unique / len(words)


def _has_internal_contradiction(text: str) -> bool:
    """Basic check for self-contradicting statements in same text."""
    sentences = re.split(r"[.!?]+", text)
    negation_words = {"not", "never", "no", "false", "incorrect", "wrong"}

    for i in range(len(sentences)):
        for j in range(i + 1, min(i + 3, len(sentences))):
            words_i = set(sentences[i].lower().split())
            words_j = set(sentences[j].lower().split())
            overlap = words_i & words_j - {"the", "a", "an", "is", "are", "was", "were"}
            if len(overlap) > 3:
                neg_i = bool(words_i & negation_words)
                neg_j = bool(words_j & negation_words)
                if neg_i != neg_j:
                    return True
    return False


# ------------------------------------------------------------
# SOURCE PROVENANCE CHAIN
# ------------------------------------------------------------

_provenance_log: List[Dict[str, Any]] = []


def record_provenance(
    item_id: str,
    source: str,
    verification_path: str,
    url_report: Optional[Dict[str, Any]] = None,
    content_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record the provenance chain for a knowledge item.
    Tracks how information entered the system and what
    validation it passed through.
    """
    entry = {
        "item_id": item_id,
        "source": source,
        "verification_path": verification_path,
        "url_integrity": url_report.get("threat_level", "not_checked") if url_report else "not_checked",
        "content_integrity": content_report.get("threat_level", "not_checked") if content_report else "not_checked",
        "timestamp": time.time(),
        "blocked": False,
    }

    if url_report and url_report.get("blocked"):
        entry["blocked"] = True
    if content_report and content_report.get("blocked"):
        entry["blocked"] = True

    _provenance_log.append(entry)
    if len(_provenance_log) > 10000:
        _provenance_log.pop(0)

    return entry


def get_provenance(item_id: str) -> Optional[Dict[str, Any]]:
    for entry in reversed(_provenance_log):
        if entry["item_id"] == item_id:
            return entry
    return None


def get_recent_threats(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent items that triggered integrity flags."""
    threats = [
        e for e in _provenance_log
        if e.get("url_integrity") not in ("none", "not_checked")
        or e.get("content_integrity") not in ("none", "not_checked")
    ]
    return threats[-limit:]


# ------------------------------------------------------------
# FULL VALIDATION PIPELINE
# ------------------------------------------------------------

def validate_source(source: str, text: str) -> Dict[str, Any]:
    """
    Full validation of a source + content pair.
    Returns a combined integrity report with a trust modifier
    that feeds into trust_scoring.compute_trust_score().
    """
    url_report = None
    content_report = validate_content(text, source)

    if "://" in source:
        url_report = validate_url(source)

    total_modifier = content_report.get("trust_modifier", 0.0)
    if url_report:
        total_modifier += url_report.get("trust_modifier", 0.0)

    blocked = content_report.get("blocked", False)
    if url_report:
        blocked = blocked or url_report.get("blocked", False)

    all_flags = list(content_report.get("flags", []))
    if url_report:
        all_flags.extend(url_report.get("flags", []))

    threat_levels = [content_report.get("threat_level", "none")]
    if url_report:
        threat_levels.append(url_report.get("threat_level", "none"))

    severity_rank = {"none": 0, "info": 1, "warning": 2, "high": 3, "critical": 4}
    max_threat = max(threat_levels, key=lambda t: severity_rank.get(t, 0))

    return {
        "source": source,
        "timestamp": time.time(),
        "passed": not blocked,
        "blocked": blocked,
        "threat_level": max_threat,
        "trust_modifier": max(-1.0, total_modifier),
        "flags": all_flags,
        "url_report": url_report,
        "content_report": content_report,
    }
