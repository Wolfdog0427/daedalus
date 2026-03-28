import unicodedata
import re

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)


class InputGateway:
    """
    Security-focused input normalization and sanitization layer.

    Responsibilities:
      - Normalize Unicode
      - Strip zero-width and control characters
      - Collapse whitespace
      - Enforce length limits
      - Detect hostile / injection-like patterns
      - Return:
          clean_text, sanitization_report, hostility_score

    HEM Integration:
      - Enter HEM when sanitizing raw user input
      - Run post-engagement checks after sanitization completes
    """

    MAX_LENGTH = 2000
    MAX_REPEATED_CHAR_RUN = 50

    SHELL_LIKE_PATTERNS = [
        r"\brm\s+-rf\b",
        r"\bcat\s+/etc/passwd\b",
        r";\s*rm\b",
        r"\|\s*sh\b",
        r"\|\s*bash\b",
        r"`[^`]*`",
        r"\$\([^)]*\)",
    ]

    SCRIPT_LIKE_PATTERNS = [
        r"<script\b",
        r"</script>",
        r"onerror\s*=",
        r"onload\s*=",
    ]

    JSON_LIKE_PATTERNS = [
        r"\{.*:.*\}",
    ]

    ZERO_WIDTH_CHARS = {
        "\u200b", "\u200c", "\u200d", "\u2060",
    }

    CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    @classmethod
    def sanitize(cls, text: str):
        if not isinstance(text, str):
            text = str(text) if text is not None else ""

        hem_maybe_enter(
            trigger_reason="input_gateway_sanitize",
            metadata={"input_preview": text[:80]},
        )

        try:
            report = {
                "original_length": len(text),
                "truncated": False,
                "removed_zero_width": False,
                "removed_control_chars": False,
                "collapsed_whitespace": False,
                "normalized_unicode": False,
                "repeated_char_runs": [],
                "matched_patterns": [],
            }

            hostility_score = 0

            normalized = unicodedata.normalize("NFC", text)
            if normalized != text:
                report["normalized_unicode"] = True
            text = normalized

            before = text
            for z in cls.ZERO_WIDTH_CHARS:
                text = text.replace(z, "")
            if text != before:
                report["removed_zero_width"] = True

            before = text
            text = cls.CONTROL_CHAR_PATTERN.sub("", text)
            if text != before:
                report["removed_control_chars"] = True

            before = text
            text = re.sub(r"\s+", " ", text).strip()
            if text != before:
                report["collapsed_whitespace"] = True

            if len(text) > cls.MAX_LENGTH:
                text = text[: cls.MAX_LENGTH]
                report["truncated"] = True
                hostility_score += 2

            repeated_runs = cls._detect_repeated_runs(text)
            if repeated_runs:
                report["repeated_char_runs"] = repeated_runs
                hostility_score += len(repeated_runs)

            matched = cls._detect_hostile_patterns(text)
            if matched:
                report["matched_patterns"] = matched
                hostility_score += 3 * len(matched)

            return text, report, hostility_score
        finally:
            try:
                hem_transition_to_postcheck()
            except Exception:
                pass
            try:
                hem_run_post_engagement_checks()
            except Exception:
                pass

    @classmethod
    def _detect_repeated_runs(cls, text: str):
        runs = []
        if not text:
            return runs

        current_char = text[0]
        current_start = 0
        current_len = 1

        for i in range(1, len(text)):
            if text[i] == current_char:
                current_len += 1
            else:
                if current_len >= cls.MAX_REPEATED_CHAR_RUN:
                    runs.append({
                        "char": current_char,
                        "length": current_len,
                        "start": current_start,
                        "end": current_start + current_len,
                    })
                current_char = text[i]
                current_start = i
                current_len = 1

        if current_len >= cls.MAX_REPEATED_CHAR_RUN:
            runs.append({
                "char": current_char,
                "length": current_len,
                "start": current_start,
                "end": current_start + current_len,
            })

        return runs

    @classmethod
    def _detect_hostile_patterns(cls, text: str):
        matches = []

        for pattern in cls.SHELL_LIKE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(f"shell:{pattern}")

        for pattern in cls.SCRIPT_LIKE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(f"script:{pattern}")

        for pattern in cls.JSON_LIKE_PATTERNS:
            if re.search(pattern, text, flags=re.DOTALL):
                matches.append(f"json_like:{pattern}")

        return matches
