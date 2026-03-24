# cli/governor_view.py

from __future__ import annotations
import json
from api.ui_gateway import handle_request


def fetch_governor_state() -> dict:
    resp = handle_request({"command": "status", "args": {}})
    return resp.get("payload", {}).get("governor", {})


def render_governor_panel() -> str:
    gov = fetch_governor_state()
    pretty = json.dumps(gov, indent=2)
    return f"=== AUTONOMY GOVERNOR ===\n{pretty}\n"
