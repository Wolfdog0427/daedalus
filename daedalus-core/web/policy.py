# web/policy.py

"""
Web Policy

Defines the WebPolicy used to govern all outbound HTTP requests.

Enforces:
- allowed domains
- blocked domains
- HTTPS-only (optional)
- basic URL validation

All actual HTTP logic lives in web/client.py.
"""

from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse
import re


@dataclass
class WebPolicy:
    allowed_domains: List[str]
    blocked_domains: List[str]
    max_content_bytes: int
    request_timeout_sec: int
    user_agent: str
    https_only: bool = True

    def is_domain_allowed(self, url: str) -> bool:
        """
        Returns True if the URL is allowed under this policy.
        """
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        scheme = parsed.scheme.lower()

        if self.https_only and scheme != "https":
            return False

        # Blocklist wins
        for pat in self.blocked_domains:
            if re.fullmatch(pat, host):
                return False

        # If no allowlist, everything (not blocked) is allowed
        if not self.allowed_domains:
            return True

        # Otherwise, host must match at least one allow pattern
        for pat in self.allowed_domains:
            if re.fullmatch(pat, host):
                return True

        return False
