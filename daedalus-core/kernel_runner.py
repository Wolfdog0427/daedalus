# kernel_runner.py
"""
Asyncio TCP IPC server for the Daedalus kernel.

Protocol: length-prefixed framing — 4-byte big-endian length header
followed by that many bytes of JSON payload.  Matches the client-side
implementation in ``server/kernel_http_api.py``.
"""

import asyncio
import json
import signal
import struct
import sys
from typing import Any, Dict

from runtime.command_console import command_console

_IPC_HEADER = struct.Struct("!I")  # 4-byte unsigned big-endian
_MAX_IPC_FRAME = 16 * 1024 * 1024  # 16 MiB — reject oversized frames


async def _read_framed(reader: asyncio.StreamReader) -> bytes:
    header = await reader.readexactly(_IPC_HEADER.size)
    (length,) = _IPC_HEADER.unpack(header)
    if length > _MAX_IPC_FRAME:
        raise ValueError(f"IPC frame too large: {length} bytes (max {_MAX_IPC_FRAME})")
    return await reader.readexactly(length)


def _frame_message(data: bytes) -> bytes:
    return _IPC_HEADER.pack(len(data)) + data


def _wrap_result(result: Any) -> Dict[str, Any]:
    """Inspect result and set ok based on common failure indicators."""
    if result is None:
        return {"ok": False, "error": "operation_returned_none", "result": result}
    if isinstance(result, dict):
        if result.get("error"):
            return {"ok": False, "result": result}
        inner_keys = {"execution", "rollback", "restoration", "snapshot", "snapshot_id", "approved", "rejected", "validation", "integrity_score"}
        for k in inner_keys:
            if k in result and result[k] is None:
                return {"ok": False, "error": "operation_failed", "result": result}
    return {"ok": True, "result": result}


async def dispatch_kernel_command(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map incoming IPC commands to CommandConsole methods."""
    payload = payload or {}

    # -- Proposal commands --

    if command == "approve_proposal":
        pid = payload.get("proposal_id")
        if pid is None:
            return {"ok": False, "error": "Missing proposal_id"}
        return _wrap_result(command_console.approve_proposal(pid))

    if command == "reject_proposal":
        pid = payload.get("proposal_id")
        if pid is None:
            return {"ok": False, "error": "Missing proposal_id"}
        return _wrap_result(command_console.reject_proposal(pid))

    # -- Execution --

    if command == "execute_next":
        return _wrap_result(command_console.execute_next())

    # -- Rollback --

    if command == "rollback":
        pid = payload.get("proposal_id")
        if pid is None:
            return {"ok": False, "error": "Missing proposal_id"}
        return _wrap_result(command_console.rollback(pid))

    # -- Snapshot / Restore --

    if command == "capture_snapshot":
        state = payload.get("state", {})
        return _wrap_result(command_console.capture_snapshot(state))

    if command == "restore_snapshot":
        sid = payload.get("snapshot_id")
        keys = payload.get("keys")
        if sid is None:
            return {"ok": False, "error": "Missing snapshot_id"}
        if keys is not None and not isinstance(keys, list):
            return {"ok": False, "error": "keys must be a list of strings or null"}
        return _wrap_result(command_console.restore(sid, keys))

    # -- Validation / Integrity --

    if command == "validate":
        return _wrap_result(command_console.validate())

    if command == "compute_integrity":
        return _wrap_result(command_console.compute_integrity_score())

    # -- Governor --

    if command == "set_governor_tier":
        tier = payload.get("tier")
        if tier is None:
            return {"ok": False, "error": "Missing tier"}
        try:
            tier_int = int(tier)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Invalid tier value: {tier!r}"}
        return _wrap_result(command_console.set_governor_tier(tier_int))

    if command == "enable_strict_mode":
        return _wrap_result(command_console.enable_strict_mode())

    if command == "disable_strict_mode":
        return _wrap_result(command_console.disable_strict_mode())

    # -- Log management --

    if command == "clear_execution_log":
        return _wrap_result(command_console.clear_execution_log())

    if command == "clear_rollback_log":
        return _wrap_result(command_console.clear_rollback_log())

    if command == "clear_restoration_log":
        return _wrap_result(command_console.clear_restoration_log())

    if command == "clear_validation_log":
        return _wrap_result(command_console.clear_validation_log())

    if command == "clear_integrity_score_history":
        return _wrap_result(command_console.clear_integrity_score_history())

    if command == "get_patches":
        try:
            from governance.patch_lifecycle import get_patches
            return {"ok": True, "patches": get_patches()}
        except ImportError:
            return {"ok": True, "patches": []}
        except Exception:
            return {"ok": False, "error": "patch_retrieval_failed", "patches": []}

    return {"ok": False, "error": f"Unknown command: {command}"}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        data = await _read_framed(reader)
        message = json.loads(data.decode())

        command = message.get("command")
        payload = message.get("payload") or {}

        if not command:
            response = {"ok": False, "error": "Missing 'command' field"}
        else:
            response = await dispatch_kernel_command(command, payload)

        resp_bytes = json.dumps(response).encode()
        writer.write(_frame_message(resp_bytes))
        await writer.drain()

    except asyncio.IncompleteReadError:
        pass
    except (json.JSONDecodeError, ValueError):
        try:
            error_bytes = json.dumps({"ok": False, "error": "Kernel error"}).encode()
            writer.write(_frame_message(error_bytes))
            await writer.drain()
        except Exception:
            pass
    except Exception:
        try:
            error_bytes = json.dumps({"ok": False, "error": "Kernel error"}).encode()
            writer.write(_frame_message(error_bytes))
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8765)
    print("Kernel listening on 127.0.0.1:8765")

    loop = asyncio.get_running_loop()

    def _shutdown_handler():
        print("Kernel shutting down gracefully…")
        server.close()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: loop.call_soon_threadsafe(_shutdown_handler))

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
