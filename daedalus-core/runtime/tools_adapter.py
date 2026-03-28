"""
Tools Adapter (Extended)

This module exposes SAFE, GOVERNED tools to the cognitive stack.
All tools:
- run through controlled wrappers
- are sandbox-safe
- return clean, normalized output
- never expose raw system capabilities
- are logged and version-aware
- integrate with the orchestrator and diagnoser

This is the ONLY place where the agent is allowed to call external tools.
"""

from typing import Optional, List, Dict, Any
from runtime.debug_tools import DebugState

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

# Web tools
from web.tools import fetch_url, search_web

# Knowledge ingestion (future expansion)
try:
    from knowledge.ingestion import ingest_text, ingest_url
    KNOWLEDGE_INGESTION_AVAILABLE = True
except Exception:
    KNOWLEDGE_INGESTION_AVAILABLE = False


# ------------------------------------------------------------
# TOOL: Fetch a URL (safe, governed, sanitized)
# ------------------------------------------------------------

def tool_fetch_url(url: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Safely fetches a URL using the Web Access Layer.
    Returns clean text only.
    Errors are returned as user-facing messages, not exceptions.
    """
    try:
        doc = fetch_url(url)
    except Exception as e:
        return f"❗ Web fetch failed: {e}"

    if debug_state and getattr(debug_state, "cockpit", False):
        print(f"[Web] Fetched {doc.get('url', url)} ({len(doc.get('text', ''))} chars)")

    return doc.get("text", "")


# ------------------------------------------------------------
# TOOL: Web Search (abstracted, API-ready)
# ------------------------------------------------------------

def tool_search_web(query: str, debug_state: Optional[DebugState] = None) -> List[Dict[str, Any]]:
    """
    Performs a web search using the configured search provider.
    Returns a list of {title, url, snippet}.
    """
    try:
        results = search_web(query)
    except Exception as e:
        return [{"error": f"❗ Web search failed: {e}"}]

    if debug_state and getattr(debug_state, "cockpit", False):
        print(f"[Web] Search '{query}' → {len(results)} results")

    return results


# ------------------------------------------------------------
# TOOL: Knowledge Ingestion (text)
# ------------------------------------------------------------

def tool_ingest_text(text: str, source: str = "manual", debug_state: Optional[DebugState] = None) -> str:
    """
    Ingests raw text into the knowledge system.
    """
    if not KNOWLEDGE_INGESTION_AVAILABLE:
        return "❗ Knowledge ingestion module not available."

    try:
        result = ingest_text(text, source=source)
    except Exception as e:
        return f"❗ Text ingestion failed: {e}"

    if debug_state and getattr(debug_state, "cockpit", False):
        print(f"[Ingest] Text ingested from source '{source}'")

    return result


# ------------------------------------------------------------
# TOOL: Knowledge Ingestion (URL)
# ------------------------------------------------------------

def tool_ingest_url(url: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Fetches a URL and ingests its content into the knowledge system.
    """
    if not KNOWLEDGE_INGESTION_AVAILABLE:
        return "❗ Knowledge ingestion module not available."

    try:
        result = ingest_url(url)
    except Exception as e:
        return f"❗ URL ingestion failed: {e}"

    if debug_state and getattr(debug_state, "cockpit", False):
        print(f"[Ingest] URL ingested: {url}")

    return result


# ------------------------------------------------------------
# TOOL: System Info (safe, minimal)
# ------------------------------------------------------------

def tool_system_info(debug_state: Optional[DebugState] = None) -> Dict[str, Any]:
    """
    Returns safe, non-sensitive system info for debugging.
    """
    info = {
        "tooling": "active",
        "web_access": True,
        "knowledge_ingestion": KNOWLEDGE_INGESTION_AVAILABLE,
    }

    if debug_state and getattr(debug_state, "cockpit", False):
        print("[System] System info requested")

    return info


# ------------------------------------------------------------
# TOOL: Text Utilities
# ------------------------------------------------------------

def tool_summarize(text: str, debug_state: Optional[DebugState] = None) -> str:
    """
    Simple summarization placeholder.
    (Your LLM handles the actual summarization.)
    """
    if not text.strip():
        return "❗ Cannot summarize empty text."

    if debug_state and getattr(debug_state, "cockpit", False):
        print(f"[Text] Summarizing {len(text)} chars")

    # The LLM will do the real summarization.
    return text[:500] + "..." if len(text) > 500 else text


# ------------------------------------------------------------
# TOOL REGISTRY
# ------------------------------------------------------------

TOOL_REGISTRY = {
    "fetch_url": tool_fetch_url,
    "search_web": tool_search_web,
    "ingest_text": tool_ingest_text,
    "ingest_url": tool_ingest_url,
    "system_info": tool_system_info,
    "summarize": tool_summarize,
}


# ------------------------------------------------------------
# TOOL DISPATCHER (HEM-protected)
# ------------------------------------------------------------

def call_tool(tool_name: str, *args, debug_state: Optional[DebugState] = None, **kwargs):
    """
    Central dispatcher for all tool calls.
    Ensures:
    - tool exists
    - tool is safe
    - tool is invoked with debug_state
    - errors are contained and user-facing

    HEM Integration:
    - Enter HEM for any external tool invocation
    - Run post-engagement checks after tool execution
    """

    # --------------------------------------------------------
    # HEM: Enter hostile engagement mode for tool invocation
    # --------------------------------------------------------
    hem_maybe_enter("tool_call", {"tool": tool_name})

    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        hem_transition_to_postcheck()
        hem_run_post_engagement_checks()
        return f"❗ Unknown tool: {tool_name}"

    try:
        result = tool(*args, debug_state=debug_state, **kwargs)
    except Exception as e:
        result = f"❗ Tool '{tool_name}' failed: {e}"

    # --------------------------------------------------------
    # HEM: Post-checks after tool execution
    # --------------------------------------------------------
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()

    return result
