# web/client.py

"""
Web Client

Low-level, policy-enforced HTTP client.

Responsibilities:
- enforce WebPolicy (domains, HTTPS, limits)
- perform HTTP GET
- cap content size
- normalize text
- attach provenance (hash, content type, timing)

All higher-level tools should use web/tools.py, not this directly.
"""

from typing import Dict, Any
import time
import hashlib
import requests

from config.web_config import WEB_POLICY
from web.policy import WebPolicy


class WebClientError(Exception):
    """Raised when a web request violates policy or fails."""


class WebClient:
    def __init__(self, policy: WebPolicy = WEB_POLICY):
        self.policy = policy

    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetches a URL under the current WebPolicy.

        Returns:
            {
                "url": str,
                "status": int,
                "elapsed_sec": float,
                "content_hash": str,
                "content_type": str,
                "text": str,
            }

        Raises:
            WebClientError on policy violation or HTTP/network failure.
        """
        if not self.policy.is_domain_allowed(url):
            raise WebClientError(f"Domain not allowed by policy: {url}")

        start = time.time()
        try:
            resp = requests.get(
                url,
                timeout=self.policy.request_timeout_sec,
                headers={"User-Agent": self.policy.user_agent},
            )
        except Exception as e:
            raise WebClientError(f"Request failed: {e}") from e

        elapsed = time.time() - start

        if not resp.ok:
            raise WebClientError(f"HTTP {resp.status_code} for {url}")

        raw = resp.content[: self.policy.max_content_bytes]
        text = raw.decode(resp.encoding or "utf-8", errors="replace")

        return {
            "url": url,
            "status": resp.status_code,
            "elapsed_sec": elapsed,
            "content_hash": self._hash_content(raw),
            "content_type": resp.headers.get("Content-Type", ""),
            "text": text,
        }
