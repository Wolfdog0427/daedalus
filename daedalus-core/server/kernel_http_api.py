from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import asyncio
import hmac
import json
import os

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
# Length-prefixed framing: 4-byte big-endian length header + JSON payload.
# Matches the protocol in kernel_runner.py.
# -----------------------------
import struct

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


async def send_to_kernel(command, payload):
    reader, writer = await asyncio.open_connection("127.0.0.1", 8765)
    try:
        msg = json.dumps({"command": command, "payload": payload}).encode()
        writer.write(_frame_message(msg))
        await writer.drain()

        response_bytes = await _read_framed(reader)
        return json.loads(response_bytes.decode())
    finally:
        writer.close()
        await writer.wait_closed()


# -----------------------------
# HTTP handlers
# -----------------------------
async def health(request):
    return JSONResponse({"ok": True})


async def get_config(request):
    if not _check_api_key(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    return JSONResponse(CURRENT_CONFIG)


_KERNEL_API_KEY = os.environ.get("DAEDALUS_API_KEY", "")


def _check_api_key(request) -> bool:
    """Validate API key if DAEDALUS_API_KEY is set. Returns True if allowed."""
    if not _KERNEL_API_KEY:
        return True
    provided = request.headers.get("X-Daedalus-Key", "")
    if not provided:
        return False
    return hmac.compare_digest(provided, _KERNEL_API_KEY)


async def handle_command(request):
    if not _check_api_key(request):
        return JSONResponse(
            {"ok": False, "error": "Unauthorized"},
            status_code=401,
        )

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "Invalid or missing JSON body"},
            status_code=400,
        )

    command = data.get("command") if isinstance(data, dict) else None
    payload = data.get("payload") if isinstance(data, dict) else None

    if not command:
        return JSONResponse(
            {"ok": False, "error": "Missing 'command' field"},
            status_code=400,
        )

    try:
        kernel_response = await send_to_kernel(command, payload)
        if isinstance(kernel_response, dict) and kernel_response.get("ok") is False:
            return JSONResponse(kernel_response, status_code=409)
        return JSONResponse(kernel_response)
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "Kernel communication failed"},
            status_code=500,
        )


async def get_patches(request):
    if not _check_api_key(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    try:
        result = await send_to_kernel("get_patches", {})
        return JSONResponse(result if isinstance(result, list) else result)
    except Exception:
        return JSONResponse({"ok": False, "error": "kernel_unavailable"}, status_code=503)


# -----------------------------
# Mount the web_router (FastAPI) so the mobile client can reach
# /tick, /proposal/{id}/approve, /status, etc. through the same
# server that exposes /command, /config, /patches.
# FastAPI is a Starlette subclass, so Mount() works natively.
# -----------------------------
def _load_web_router():
    try:
        from runtime.web_router import app as web_router_app
        return web_router_app
    except Exception:
        return None


_web_router = _load_web_router()

routes = [
    Route("/health", health, methods=["GET"]),
    Route("/config", get_config, methods=["GET"]),
    Route("/command", handle_command, methods=["POST"]),
    Route("/patches", get_patches, methods=["GET"]),
]

if _web_router is not None:
    routes.append(Mount("/api", app=_web_router))

app = Starlette(
    debug=False,
    routes=routes,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                           "http://localhost:8000", "http://127.0.0.1:8000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
)
