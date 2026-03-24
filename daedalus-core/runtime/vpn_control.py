# runtime/vpn_control.py

from __future__ import annotations
from typing import Dict, Any
import subprocess


def _run_command(args: list[str]) -> Dict[str, Any]:
    """
    Run a shell command and capture stdout/stderr safely.
    Designed for Termux on Android.
    """
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Command not found: {args[0]}",
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Exception while running {' '.join(args)}: {e}",
        }


def connect_vpn() -> str:
    """
    Request VPN connect via the official Tailscale Android app.

    Uses the Android intent:
      am start -a android.intent.action.VIEW -d "tailscale://up"
    """
    result = _run_command([
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        "tailscale://up",
    ])

    if result["ok"]:
        return "✓ VPN connect requested via Tailscale app."
    detail = result["stderr"] or result["stdout"] or "(no details)"
    return f"⚠ Failed to request VPN connect via Tailscale.\n{detail}"


def disconnect_vpn() -> str:
    """
    Request VPN disconnect via the official Tailscale Android app.

    Uses the Android intent:
      am start -a android.intent.action.VIEW -d "tailscale://down"
    """
    result = _run_command([
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        "tailscale://down",
    ])

    if result["ok"]:
        return "✓ VPN disconnect requested via Tailscale app."
    detail = result["stderr"] or result["stdout"] or "(no details)"
    return f"⚠ Failed to request VPN disconnect via Tailscale.\n{detail}"


def vpn_status() -> str:
    """
    Best-effort VPN status.

    If the Tailscale CLI is available in Termux, we use:
      tailscale status

    Otherwise, we fall back to a generic message noting that
    the Android app controls the connection state.
    """
    result = _run_command(["tailscale", "status"])

    if result["ok"]:
        out = result["stdout"] or "(no output)"
        return f"📡 VPN status (tailscale CLI):\n{out}"

    return (
        "📡 VPN status is unknown from Termux.\n"
        "The Tailscale Android app controls the VPN connection state.\n"
        "If you want richer status here, install the Tailscale CLI in Termux."
    )
