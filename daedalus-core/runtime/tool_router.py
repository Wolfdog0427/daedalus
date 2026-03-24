"""
Tool Router

Provides a thin, explicit routing layer between:
- resolvers / intent handlers
- the tools adapter

This keeps your resolvers clean: they decide *what* to do,
and the router decides *which tool* to call and *how*.
"""

from typing import Optional, Dict, Any

# ------------------------------------------------------------
# HEM imports (Option C deep integration for external tools)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

from runtime.debug_tools import DebugState
from runtime.tools_adapter import call_tool


def invoke_fetch_url(url: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Resolver-level helper to fetch a URL.

    HEM:
    - Enter HEM for external URL fetch
    - Run post-engagement checks after tool call
    """
    hem_maybe_enter(trigger_reason="tool_fetch_url", metadata={"url": url})
    result = call_tool("fetch_url", url, debug_state=debug_state)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


def invoke_search_web(query: str, debug_state: Optional[DebugState] = None):
    """
    Resolver-level helper to perform a web search.

    HEM:
    - Enter HEM for web search
    - Run post-engagement checks after tool call
    """
    hem_maybe_enter(trigger_reason="tool_search_web", metadata={"query": query})
    result = call_tool("search_web", query, debug_state=debug_state)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


def invoke_ingest_text(
    text: str,
    source: str = "manual",
    debug_state: Optional[DebugState] = None,
) -> str:
    """
    Resolver-level helper to ingest raw text into knowledge.

    Note:
    - This is typically local/manual input; we do not force HEM here.
    - If you later treat certain sources as hostile, you can wrap them in HEM.
    """
    return call_tool("ingest_text", text, source=source, debug_state=debug_state)


def invoke_ingest_url(url: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Resolver-level helper to ingest a URL into knowledge.

    HEM:
    - Enter HEM for external URL ingestion
    - Run post-engagement checks after tool call
    """
    hem_maybe_enter(trigger_reason="tool_ingest_url", metadata={"url": url})
    result = call_tool("ingest_url", url, debug_state=debug_state)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


def invoke_system_info(debug_state: Optional[DebugState] = None) -> Dict[str, Any]:
    """
    Resolver-level helper to get safe system info.
    """
    return call_tool("system_info", debug_state=debug_state)


def invoke_summarize(text: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Resolver-level helper to summarize text.
    """
    return call_tool("summarize", text, debug_state=debug_state)
