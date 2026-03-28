# app.py

from __future__ import annotations
import argparse
import uvicorn

from api.http_api import app as http_app
from runtime.health_dashboard import print_health_summary
from runtime.logging_manager import log_event
from runtime.startup_diagnostics import run_startup_diagnostics


def startup_health_check() -> None:
    """
    Run startup diagnostics and print a health summary.
    Abort startup if critical components are not ready.
    """
    print("Performing startup health check…")
    diag = run_startup_diagnostics()

    if not diag["state_sources_ok"]:
        print("❌ Startup failed: state sources not OK")
        print(diag)
        raise SystemExit(1)

    if not diag["patch_history_integrity"]:
        print("❌ Startup failed: patch history corrupted")
        print(diag)
        raise SystemExit(1)

    print("✅ Startup health check passed")
    print_health_summary()


def start_http_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Start the HTTP API server.
    """
    log_event("app", "Starting HTTP API server", {"host": host, "port": port})
    uvicorn.run(http_app, host=host, port=port)


def start_cli() -> None:
    """
    Start the CLI console.
    """
    from cli.console import main as cli_main
    cli_main()


def start_knowledge_console() -> None:
    """
    Start the interactive knowledge-side command console.
    """
    from knowledge.command_console import start_console
    start_console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Assistant Core Application")
    parser.add_argument(
        "mode",
        choices=["http", "cli", "console", "health"],
        help="Start mode: http server, CLI, knowledge console, or health check",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)

    ns = parser.parse_args()

    if ns.mode in ("http", "health"):
        startup_health_check()

    if ns.mode == "http":
        start_http_server(ns.host, ns.port)

    elif ns.mode == "cli":
        try:
            startup_health_check()
        except SystemExit:
            print("⚠ Startup health check failed — entering CLI in degraded mode.")
        start_cli()

    elif ns.mode == "console":
        try:
            startup_health_check()
        except SystemExit:
            print("⚠ Startup health check failed — entering console in degraded mode.")
        start_knowledge_console()

    elif ns.mode == "health":
        return


if __name__ == "__main__":
    main()
