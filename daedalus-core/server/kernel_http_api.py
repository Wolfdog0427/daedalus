from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import asyncio
import json

# -----------------------------
# Simple in-memory config placeholder
# (can be wired to real kernel config later)
# -----------------------------
CURRENT_CONFIG = {
    "layoutVariant": "comfortable",
    "showDebugBanner": True,
}

# -----------------------------
# IPC bridge to kernel process
# -----------------------------
async def send_to_kernel(command, payload):
    reader, writer = await asyncio.open_connection("127.0.0.1", 8765)

    message = json.dumps({"command": command, "payload": payload})
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(65536)
    writer.close()

    return json.loads(data.decode())


# -----------------------------
# HTTP handlers
# -----------------------------
async def health(request):
    return JSONResponse({"ok": True})


async def get_config(request):
    # For now, return static config; can be replaced with kernel-backed config
    return JSONResponse(CURRENT_CONFIG)


async def handle_command(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    command = data.get("command")
    payload = data.get("payload")

    if not command:
        return JSONResponse(
            {"ok": False, "error": "Missing 'command' field"},
            status_code=400,
        )

    try:
        kernel_response = await send_to_kernel(command, payload)
        return JSONResponse(kernel_response)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"Kernel communication failed: {e}"},
            status_code=500,
        )


async def get_patches(request):
    # Placeholder: wire this to kernel patch/proposal state when ready
    return JSONResponse([])


# -----------------------------
# Starlette app
# -----------------------------
routes = [
    Route("/health", health),
    Route("/config", get_config),
    Route("/command", handle_command, methods=["POST"]),
    Route("/patches", get_patches),
]

app = Starlette(debug=False, routes=routes)
