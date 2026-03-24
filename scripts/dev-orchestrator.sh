#!/usr/bin/env bash
set -euo pipefail

# Start the Daedalus orchestrator in development mode.
# Defaults to port 4000; override with ORCHESTRATOR_PORT env var.

cd "$(dirname "$0")/../orchestrator"

if [ ! -d node_modules ]; then
  echo "[dev-orchestrator] installing dependencies…"
  npm install
fi

echo "[dev-orchestrator] starting on port ${ORCHESTRATOR_PORT:-4000}"
exec npm run dev
