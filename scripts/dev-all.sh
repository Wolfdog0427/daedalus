#!/usr/bin/env bash
set -euo pipefail

# Start both orchestrator and cockpit in development mode.
# The orchestrator runs in the background; the cockpit runs in the foreground.

SCRIPT_DIR="$(dirname "$0")"

echo "[dev-all] starting orchestrator…"
bash "$SCRIPT_DIR/dev-orchestrator.sh" &
ORCH_PID=$!

# Give the orchestrator a moment to bind its port
sleep 2

echo "[dev-all] starting cockpit…"
bash "$SCRIPT_DIR/dev-cockpit.sh" &
COCKPIT_PID=$!

trap 'echo "[dev-all] shutting down…"; kill $ORCH_PID $COCKPIT_PID 2>/dev/null; wait' EXIT

echo "[dev-all] orchestrator PID=$ORCH_PID, cockpit PID=$COCKPIT_PID"
echo "[dev-all] press Ctrl+C to stop both"
wait
