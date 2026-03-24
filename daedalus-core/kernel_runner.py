# kernel_runner.py

import asyncio
import json
from typing import Any, Dict

from runtime.command_console import command_console


async def dispatch_kernel_command(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map incoming IPC commands to CommandConsole methods.
    This matches the mobile UI command bindings.
    """

    payload = payload or {}

    if command == "approve_proposal":
        pid = payload.get("proposal_id")
        if not pid:
            return {"ok": False, "error": "Missing proposal_id"}
        return {"ok": True, "result": command_console.approve_proposal(pid)}

    if command == "reject_proposal":
        pid = payload.get("proposal_id")
        if not pid:
            return {"ok": False, "error": "Missing proposal_id"}
        return {"ok": True, "result": command_console.reject_proposal(pid)}

    if command == "restore_snapshot":
        sid = payload.get("snapshot_id")
        keys = payload.get("keys")
        if not sid:
            return {"ok": False, "error": "Missing snapshot_id"}
        return {"ok": True, "result": command_console.restore(sid, keys)}

    if command == "validate":
        return {"ok": True, "result": command_console.validate()}

    if command == "compute_integrity":
        return {"ok": True, "result": command_console.compute_integrity_score()}

    return {"ok": False, "error": f"Unknown command: {command}"}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        data = await reader.read(65536)
        message = json.loads(data.decode())

        command = message.get("command")
        payload = message.get("payload") or {}

        if not command:
            response = {"ok": False, "error": "Missing 'command' field"}
        else:
            response = await dispatch_kernel_command(command, payload)

        writer.write(json.dumps(response).encode())
        await writer.drain()

    except Exception as e:
        error_resp = {"ok": False, "error": f"Kernel error: {e}"}
        writer.write(json.dumps(error_resp).encode())
        await writer.drain()
    finally:
        writer.close()


async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8765)
    print("Kernel listening on 127.0.0.1:8765")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
