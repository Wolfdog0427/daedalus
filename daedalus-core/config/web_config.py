# config/web_config.py

"""
Web Access Safety Configuration

This module defines the WebPolicy used by the WebClient.
It governs:
- allowed domains
- blocked domains
- HTTPS-only enforcement
- maximum content size
- request timeouts
- user agent identity

This file is intentionally simple and declarative.
All enforcement happens in web/policy.py and web/client.py.
"""

from web.policy import WebPolicy

# ------------------------------------------------------------
# DOMAIN SAFETY POLICY
# ------------------------------------------------------------

# These patterns are regexes matched against the hostname.
# You can expand this list as trust grows.
ALLOWED_DOMAINS = [
    r".*\.wikipedia\.org",
    r"docs\.python\.org",
    r"developer\.mozilla\.org",
    r"www\.w3\.org",
    r"www\.ietf\.org",
    r".*\.mit\.edu",
    r".*\.stanford\.edu",
    r".*\.harvard\.edu",
    r".*\.gov",
    r".*\.edu",
]

# Explicitly blocked domains (regex patterns)
BLOCKED_DOMAINS = [
    r".*\.example-malware\.com",
    r".*\.clickbait-news\.xyz",
    r".*\.tracking-ads\.net",
]

# ------------------------------------------------------------
# WEB POLICY OBJECT
# ------------------------------------------------------------

WEB_POLICY = WebPolicy(
    allowed_domains=ALLOWED_DOMAINS,
    blocked_domains=BLOCKED_DOMAINS,
    max_content_bytes=512_000,        # 500 KB per request
    request_timeout_sec=10,           # 10-second timeout
    user_agent="Spencer-Agent/1.0",   # Identifies your system safely
    https_only=True,                  # Enforce HTTPS for all requests
)
