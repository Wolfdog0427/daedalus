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
import threading
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse
from collections import Counter, deque

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
    "i": ["\u0456", "\u00ec", "\u00ed", "\u012b"],
    "l": ["\u0031", "\u007c", "\u0049"],
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
        threshold = max(len(trusted_base) - 1, int(len(trusted_base) * 0.75))
        if len(host_base) >= len(trusted_base) - 1:
            common = sum(1 for a, b in zip(trusted_base, host_base) if a == b)
            if common >= threshold and host != trusted:
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
    _hem_entered = False
    if _HEM_AVAILABLE:
        try:
            hem_maybe_enter(
                trigger_reason="source_integrity_content_validation",
                metadata={"source": source, "text_length": len(text)},
            )
            _hem_entered = True
        except Exception:
            pass

    try:
        # Cross-check with InputGateway hostile pattern detection
        # NOTE: InputGateway.sanitize() has its own HEM calls but the
        # re-entry guard prevents double-enter; we must NOT let its
        # cleanup end our outer HEM session. Call raw pattern logic only.
        if _INPUT_GATEWAY_AVAILABLE:
            try:
                _, gw_report, hostility_score = InputGateway.sanitize(text[:2000])
                if hostility_score >= 3:
                    _flag(report, "input_gateway_hostile", 0.5, "high")
                for pattern in gw_report.get("matched_patterns", []):
                    _flag(report, f"gateway:{pattern}", 0.3, "warning")
            except Exception:
                _flag(report, "input_gateway_error", 0.4, "warning")

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
    finally:
        if _hem_entered and _HEM_AVAILABLE:
            try:
                hem_transition_to_postcheck()
            except Exception:
                pass
            try:
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
            overlap = (words_i & words_j) - {"the", "a", "an", "is", "are", "was", "were"}
            if len(overlap) > 3:
                neg_i = bool(words_i & negation_words)
                neg_j = bool(words_j & negation_words)
                if neg_i != neg_j:
                    return True
    return False


# ------------------------------------------------------------
# SOURCE PROVENANCE CHAIN
# ------------------------------------------------------------

_provenance_log: deque = deque(maxlen=50000)
_provenance_lock = threading.Lock()


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

    with _provenance_lock:
        _provenance_log.append(entry)

    return dict(entry)


def get_provenance(item_id: str) -> Optional[Dict[str, Any]]:
    with _provenance_lock:
        snapshot = list(_provenance_log)
    for entry in reversed(snapshot):
        if entry["item_id"] == item_id:
            return dict(entry)
    return None


def get_recent_threats(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent items that triggered integrity flags."""
    with _provenance_lock:
        snapshot = list(_provenance_log)
    threats = [
        dict(e) for e in snapshot
        if e.get("url_integrity") not in ("none", "not_checked")
        or e.get("content_integrity") not in ("none", "not_checked")
    ]
    n = max(0, int(limit))
    return threats[-n:] if n > 0 else []


# ------------------------------------------------------------
# ATTACK WINDOW TRACKING & POST-ATTACK SWEEP (F9)
# ------------------------------------------------------------

_attack_windows: deque = deque(maxlen=2000)
_attack_lock = threading.Lock()


def record_attack_event(source: str, threat_level: str, timestamp: Optional[float] = None) -> None:
    """Record that an attack was detected from a source at a given time."""
    with _attack_lock:
        _attack_windows.append({
            "source": source,
            "threat_level": threat_level,
            "detected_at": timestamp or time.time(),
            "swept": False,
        })
    # deque(maxlen=2000) handles eviction automatically


def sweep_attack_window(
    window_start: float,
    window_end: float,
    reverify_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Re-verify items ingested during an attack window.
    Scans the provenance log for items ingested between window_start
    and window_end, then re-runs verification on each.

    Args:
        window_start: epoch timestamp for start of attack window
        window_end: epoch timestamp for end of attack window
        reverify_fn: callable(item_id, source) -> bool that re-verifies
                     an item. If None, items are flagged but not re-verified.

    Returns:
        Summary of items found, re-verified, and flagged.
    """
    with _provenance_lock:
        candidates = [
            dict(entry) for entry in _provenance_log
            if window_start <= entry.get("timestamp", 0) <= window_end
            and not entry.get("blocked", False)
        ]

    report: Dict[str, Any] = {
        "window_start": window_start,
        "window_end": window_end,
        "items_in_window": len(candidates),
        "reverified": 0,
        "flagged": 0,
        "errors": 0,
    }

    for entry in candidates:
        item_id = entry.get("item_id", "")
        source = entry.get("source", "")
        if not item_id:
            continue

        if reverify_fn is not None:
            try:
                passed = reverify_fn(item_id, source)
                if passed:
                    report["reverified"] += 1
                else:
                    report["flagged"] += 1
                    entry["post_attack_flagged"] = True
            except Exception:
                report["errors"] += 1
        else:
            report["flagged"] += 1
            entry["post_attack_flagged"] = True

    with _attack_lock:
        for aw in _attack_windows:
            if aw["detected_at"] >= window_start and aw["detected_at"] <= window_end:
                aw["swept"] = True

    return report


def get_unswept_attack_windows() -> List[Dict[str, Any]]:
    """Return attack events that haven't been swept yet."""
    with _attack_lock:
        return [dict(aw) for aw in _attack_windows if not aw["swept"]]


# ------------------------------------------------------------
# DELAYED POISONING DETECTION (Sim-fix M2)
# ------------------------------------------------------------

def run_delayed_poison_audit(
    sample_size: int = 100,
    reverify_fn: Optional[Any] = None,
    estimated_contaminated: int = 0,
    active_items: int = 0,
) -> Dict[str, Any]:
    """
    Targeted audit of verified items for delayed poisoning.

    Priority tiers:
    1. Items ingested near attack windows (highest priority)
    2. Uncorroborated long-resident items (C1: corroboration pressure)
    3. Most recently ingested items (recency bias)
    4. Random fill from remaining provenance

    Enhancements:
    - C1: uncorroborated items get a dedicated priority tier
    - C4: provider-assisted deep check on flagged candidates
    - C5: contamination budget multiplier scales sample size
    """
    import random

    with _provenance_lock:
        prov_snapshot = list(_provenance_log)
    if not prov_snapshot:
        return {"action": "skipped", "reason": "no_provenance_data"}

    # C5: scale sample size by contamination pressure
    pressure = compute_contamination_pressure(estimated_contaminated, active_items)
    effective_sample = int(sample_size * pressure["multiplier"])

    sample: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    budget = min(effective_sample, len(prov_snapshot))

    # Priority 1: Items near attack windows (within 1800s of any attack)
    with _attack_lock:
        attack_times = [aw["detected_at"] for aw in _attack_windows]
    if attack_times:
        for entry in prov_snapshot:
            if len(sample) >= budget // 2:
                break
            ts = entry.get("timestamp", 0)
            item_id = entry.get("item_id", "")
            if not item_id or item_id in seen_ids or entry.get("blocked"):
                continue
            near_attack = any(abs(ts - at) < 1800 for at in attack_times)
            if near_attack:
                sample.append(entry)
                seen_ids.add(item_id)

    # Priority 2 (C1): Uncorroborated long-resident items
    uncorroborated = get_uncorroborated_items(min_age=86400 * 30)
    for entry in uncorroborated:
        if len(sample) >= budget * 3 // 4:
            break
        item_id = entry.get("item_id", "")
        if item_id in seen_ids:
            continue
        sample.append(entry)
        seen_ids.add(item_id)

    # Priority 3: Most recent items (last 20% of provenance)
    from itertools import islice
    recency_start = max(0, len(prov_snapshot) - len(prov_snapshot) // 5)
    for entry in islice(prov_snapshot, recency_start, None):
        if len(sample) >= budget:
            break
        item_id = entry.get("item_id", "")
        if not item_id or item_id in seen_ids or entry.get("blocked"):
            continue
        sample.append(entry)
        seen_ids.add(item_id)

    # Priority 4: Random fill
    remaining = [
        e for e in prov_snapshot
        if e.get("item_id") and e["item_id"] not in seen_ids and not e.get("blocked")
    ]
    fill_count = budget - len(sample)
    if fill_count > 0 and remaining:
        sample.extend(random.sample(remaining, min(fill_count, len(remaining))))

    audited = 0
    flagged = 0
    errors = 0
    taint_propagated = 0

    for entry in sample:
        item_id = entry.get("item_id", "")
        source = entry.get("source", "")
        if not item_id or entry.get("blocked"):
            continue

        audited += 1

        try:
            if "://" in source:
                url_check = validate_url(source)
                if url_check.get("blocked"):
                    with _provenance_lock:
                        entry["delayed_poison_flagged"] = True
                    flagged += 1
                    result = propagate_taint(item_id)
                    taint_propagated += result.get("propagated", 0)
                    continue

            if reverify_fn is not None:
                passed = reverify_fn(item_id, source)
                if not passed:
                    with _provenance_lock:
                        entry["delayed_poison_flagged"] = True
                    flagged += 1
                    result = propagate_taint(item_id)
                    taint_propagated += result.get("propagated", 0)
        except Exception:
            errors += 1

    # C4: provider-assisted deep check on unflagged high-risk items
    provider_result = run_provider_assisted_audit(
        [e for e in sample if not e.get("delayed_poison_flagged")],
        max_checks=min(20, len(sample) // 5 + 1),
    )

    return {
        "action": "delayed_poison_audit",
        "sample_size": len(sample),
        "effective_sample_size": effective_sample,
        "audited": audited,
        "flagged": flagged,
        "taint_propagated": taint_propagated,
        "errors": errors,
        "contamination_pressure": pressure,
        "provider_audit": provider_result,
        "targeting": "attack_window+uncorroborated+recency+random",
    }


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

    # P4: Quarantine items with warning-level threats instead of
    # letting them through. They enter a holding queue for deeper
    # verification before being ingested.
    quarantine = False
    if not blocked and max_threat in ("warning", "high"):
        quarantine = True

    return {
        "source": source,
        "timestamp": time.time(),
        "passed": not blocked,
        "blocked": blocked,
        "quarantine": quarantine,
        "threat_level": max_threat,
        "trust_modifier": max(-1.0, total_modifier),
        "flags": all_flags,
        "url_report": url_report,
        "content_report": content_report,
    }


# ------------------------------------------------------------
# QUARANTINE SYSTEM (P4)
# ------------------------------------------------------------

_quarantine_queue: deque = deque(maxlen=5000)
_quarantine_lock = threading.Lock()


def quarantine_item(item_id: str, source: str, text: str, reason: str) -> None:
    """Place an item in quarantine for deeper verification."""
    with _quarantine_lock:
        _quarantine_queue.append({
            "item_id": item_id,
            "source": source,
            "text_preview": text[:200],
            "reason": reason,
            "quarantined_at": time.time(),
            "status": "pending",
        })


def review_quarantine(
    reverify_fn: Optional[Any] = None,
    max_review: int = 50,
) -> Dict[str, Any]:
    """
    Review quarantined items. Each item gets deep re-verification.
    Items that pass are released; items that fail are permanently
    flagged. Items older than 24h without review are auto-flagged.

    This is the system's last line of defense: even if a poisoned
    item slips through the integrity check with a "warning" threat
    level, it sits in quarantine until explicitly cleared.
    """
    reviewed = 0
    released = 0
    flagged = 0
    auto_flagged = 0
    now = time.time()

    with _quarantine_lock:
        pending = [q for q in _quarantine_queue if q["status"] == "pending"]

    for entry in pending[:max_review]:
        reviewed += 1
        age_hours = (now - entry["quarantined_at"]) / 3600

        if age_hours > 48:
            with _quarantine_lock:
                entry["status"] = "auto_flagged"
            auto_flagged += 1
            continue

        if reverify_fn is not None:
            try:
                passed = reverify_fn(entry["item_id"], entry["source"])
                with _quarantine_lock:
                    if passed:
                        entry["status"] = "released"
                        released += 1
                    else:
                        entry["status"] = "flagged"
                        flagged += 1
            except Exception:
                with _quarantine_lock:
                    entry["status"] = "flagged"
                flagged += 1
        else:
            source = entry.get("source", "")
            if "://" in source:
                url_check = validate_url(source)
                with _quarantine_lock:
                    if url_check.get("blocked"):
                        entry["status"] = "flagged"
                        flagged += 1
                    else:
                        entry["status"] = "released"
                        released += 1
            else:
                with _quarantine_lock:
                    entry["status"] = "released"
                released += 1

    with _quarantine_lock:
        queue_pending = sum(1 for q in _quarantine_queue if q["status"] == "pending")

    return {
        "action": "quarantine_review",
        "reviewed": reviewed,
        "released": released,
        "flagged": flagged,
        "auto_flagged": auto_flagged,
        "queue_size": queue_pending,
    }


def get_quarantine_status() -> Dict[str, Any]:
    with _quarantine_lock:
        pending = sum(1 for q in _quarantine_queue if q["status"] == "pending")
        released = sum(1 for q in _quarantine_queue if q["status"] == "released")
        flagged = sum(1 for q in _quarantine_queue if q["status"] in ("flagged", "auto_flagged"))
        total = len(_quarantine_queue)
    return {
        "queue_total": total,
        "pending": pending,
        "released": released,
        "flagged": flagged,
    }


# ------------------------------------------------------------
# CORROBORATION TRACKING (C1)
# ------------------------------------------------------------

_corroboration_map: Dict[str, Dict[str, Any]] = {}
_corroboration_lock = threading.Lock()


def record_corroboration(item_id: str) -> None:
    """Record that an item has been independently corroborated by
    new ingested data (e.g., a new item references or confirms it).
    Legitimate items naturally accumulate corroborations over time;
    contaminated items tend to remain isolated."""
    with _corroboration_lock:
        if item_id in _corroboration_map:
            _corroboration_map[item_id]["count"] += 1
            _corroboration_map[item_id]["last_corroborated"] = time.time()
        else:
            _corroboration_map[item_id] = {
                "count": 1,
                "last_corroborated": time.time(),
            }


def get_uncorroborated_items(min_age: float = 86400 * 30) -> List[Dict[str, Any]]:
    """Return provenance entries for items that have never been
    independently corroborated and are older than min_age seconds.
    These are prime candidates for contamination."""
    now = time.time()
    with _provenance_lock:
        prov_snapshot = list(_provenance_log)
    with _corroboration_lock:
        corr_snapshot = dict(_corroboration_map)
    uncorroborated = []
    for entry in prov_snapshot:
        item_id = entry.get("item_id", "")
        if not item_id or entry.get("blocked"):
            continue
        age = now - entry.get("timestamp", now)
        if age < min_age:
            continue
        corr = corr_snapshot.get(item_id)
        if corr is None or corr["count"] == 0:
            uncorroborated.append(dict(entry))
    return uncorroborated


# ------------------------------------------------------------
# SOURCE-CHAIN TAINT PROPAGATION (C2)
# ------------------------------------------------------------

TAINT_WINDOW = 1800  # seconds: same-source items within 30 min are suspect


def propagate_taint(
    discovered_item_id: str,
    discovery_timestamp: Optional[float] = None,
) -> Dict[str, Any]:
    """
    When a contaminated item is discovered, trace its provenance chain
    and quarantine same-source, near-timestamp items.

    Attackers typically inject multiple poisoned items in a burst from
    the same source. Each individual discovery should cascade into a
    chain audit — multiplying the effectiveness of every sweep hit.
    """
    source_entry = get_provenance(discovered_item_id)
    if source_entry is None:
        return {"action": "taint_propagation", "propagated": 0,
                "reason": "no_provenance"}

    source = source_entry.get("source", "")
    ts = source_entry.get("timestamp", 0)

    with _provenance_lock:
        candidates = [
            e for e in _provenance_log
            if e.get("source") == source
            and abs(e.get("timestamp", 0) - ts) < TAINT_WINDOW
            and e.get("item_id") != discovered_item_id
            and not e.get("blocked")
            and not e.get("post_attack_flagged")
            and not e.get("taint_flagged")
        ]
        for entry in candidates:
            entry["taint_flagged"] = True

    propagated = 0
    for entry in candidates:
        quarantine_item(
            entry.get("item_id", ""),
            entry.get("source", ""),
            "",
            f"taint_propagation_from:{discovered_item_id}",
        )
        propagated += 1

    return {
        "action": "taint_propagation",
        "source_item": discovered_item_id,
        "source": source,
        "window_seconds": TAINT_WINDOW,
        "candidates_found": len(candidates),
        "propagated": propagated,
    }


# ------------------------------------------------------------
# CONTAMINATION BUDGET CEILING (C5)
# ------------------------------------------------------------

CONTAMINATION_BUDGET_RATE = 0.003  # 0.3% of active items is the ceiling


def compute_contamination_pressure(
    estimated_contaminated: int,
    active_items: int,
) -> Dict[str, Any]:
    """
    Compute contamination pressure relative to the system's budget.

    When the contamination rate exceeds the budget, returns a multiplier
    > 1.0 that callers should use to amplify sweep frequency, audit
    depth, and ingestion screening intensity. This creates a self-
    correcting feedback loop: high contamination triggers aggressive
    defense until the rate returns to budget.
    """
    if active_items == 0:
        return {"pressure": 0.0, "over_budget": False, "multiplier": 1.0}

    rate = estimated_contaminated / active_items
    budget = CONTAMINATION_BUDGET_RATE

    if rate <= budget:
        return {
            "pressure": round(rate / budget, 4),
            "over_budget": False,
            "multiplier": 1.0,
        }

    excess = (rate - budget) / budget
    multiplier = min(3.0, 1.0 + excess)
    return {
        "pressure": round(rate / budget, 4),
        "over_budget": True,
        "multiplier": round(multiplier, 4),
    }


# ------------------------------------------------------------
# STATISTICAL CLUSTER ANOMALY DETECTION (C3)
# ------------------------------------------------------------

def detect_source_anomalies(
    min_items_per_source: int = 5,
    flag_rate_threshold: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Group provenance entries by source and detect anomalous sources.

    A source is anomalous if:
    - Its flag rate (post_attack_flagged, delayed_poison_flagged,
      taint_flagged) exceeds the threshold
    - It has disproportionate temporal clustering (many items in
      a short burst vs. steady ingestion)

    Returns a list of anomalous source profiles for further
    investigation. Does NOT auto-flag or quarantine — callers
    decide the response.
    """
    from collections import defaultdict as _dd

    with _provenance_lock:
        prov_snapshot = list(_provenance_log)
    source_groups: Dict[str, List[Dict[str, Any]]] = _dd(list)
    for entry in prov_snapshot:
        src = entry.get("source", "")
        if src and not entry.get("blocked"):
            source_groups[src].append(entry)

    anomalies = []
    for src, entries in source_groups.items():
        if len(entries) < min_items_per_source:
            continue

        total = len(entries)
        flagged = sum(
            1 for e in entries
            if e.get("post_attack_flagged")
            or e.get("delayed_poison_flagged")
            or e.get("taint_flagged")
        )
        flag_rate = flagged / total

        timestamps = sorted(e.get("timestamp", 0) for e in entries)
        if len(timestamps) >= 2:
            span = timestamps[-1] - timestamps[0]
            avg_gap = span / (len(timestamps) - 1) if span > 0 else 0
        else:
            avg_gap = 0

        burst_score = 0.0
        if avg_gap > 0:
            burst_count = sum(
                1 for i in range(1, len(timestamps))
                if timestamps[i] - timestamps[i - 1] < avg_gap * 0.1
            )
            burst_score = burst_count / max(1, len(timestamps) - 1)

        is_anomalous = flag_rate > flag_rate_threshold or burst_score > 0.5

        if is_anomalous:
            anomalies.append({
                "source": src,
                "total_items": total,
                "flagged_items": flagged,
                "flag_rate": round(flag_rate, 4),
                "burst_score": round(burst_score, 4),
                "reasons": [
                    r for r in [
                        "high_flag_rate" if flag_rate > flag_rate_threshold else None,
                        "burst_pattern" if burst_score > 0.5 else None,
                    ] if r
                ],
            })

    anomalies.sort(key=lambda a: a["flag_rate"], reverse=True)
    return anomalies


# ------------------------------------------------------------
# PROVIDER-ASSISTED DEEP AUDIT (C4)
# ------------------------------------------------------------

def run_provider_assisted_audit(
    sample: List[Dict[str, Any]],
    max_checks: int = 20,
) -> Dict[str, Any]:
    """
    Use an LLM/AGI provider to perform deep consistency checks on
    a sample of items. The provider analyzes whether each item is
    factually consistent with the broader knowledge graph.

    Falls back gracefully if no provider is available.
    """
    try:
        from knowledge.llm_adapter import llm_adapter
        if not llm_adapter.is_available():
            return {"action": "provider_audit", "available": False}
    except ImportError:
        return {"action": "provider_audit", "available": False}

    checked = 0
    flagged = 0

    for entry in sample[:max_checks]:
        item_id = entry.get("item_id", "")
        source = entry.get("source", "")
        if not item_id:
            continue

        try:
            result = llm_adapter.assess_domain_relevance(
                domain=f"verify_item:{item_id}",
                existing_entities=[],
                blind_spots=[],
            )
            checked += 1
            if result.get("available") and result.get("relevance", 1.0) < 0.3:
                with _provenance_lock:
                    entry["provider_flagged"] = True
                flagged += 1
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "provider audit check failed for %s: %s", item_id, exc,
            )

    return {
        "action": "provider_audit",
        "available": True,
        "checked": checked,
        "flagged": flagged,
    }
