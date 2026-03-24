# web/tools.py

"""
Web Tools

High-level, SAFE web tools exposed to the cognitive stack.

This module wraps the low-level WebClient and provides:
- fetch_url: fetch a single URL with provenance and safety
- search_web: abstracted search interface (API-ready, currently placeholder)

All web access is governed by:
- config/web_config.WEB_POLICY
- web/policy.WebPolicy
- web/client.WebClient

No code outside this module should perform raw HTTP.
"""

from typing import Dict, Any, List
from web.client import WebClient, WebClientError

# Single shared client instance governed by WEB_POLICY
_web_client = WebClient()


# ------------------------------------------------------------
# FETCH URL
# ------------------------------------------------------------

def fetch_url(url: str) -> Dict[str, Any]:
    """
    Safely fetch a URL using the WebClient.

    Returns a dict:
        {
            "url": str,
            "status": int,
            "elapsed_sec": float,
            "content_hash": str,
            "content_type": str,
            "text": str,
        }

    Raises:
        WebClientError on policy violations or network/HTTP issues.
    """
    return _web_client.fetch(url)


# ------------------------------------------------------------
# SEARCH WEB (ABSTRACTED, API-READY)
# ------------------------------------------------------------

def search_web(query: str) -> List[Dict[str, Any]]:
    """
    Performs a web search for the given query.

    This is an abstraction layer intended to be wired to a real search API
    (e.g., Bing, custom search, internal index).

    Expected return format:
        [
            {
                "title": str,
                "url": str,
                "snippet": str,
            },
            ...
        ]

    For now, this is a placeholder that must be implemented when a search
    provider is chosen.
    """
    raise NotImplementedError("search_web is not wired to a real search API yet.")
