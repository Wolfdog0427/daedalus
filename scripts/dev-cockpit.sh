#!/usr/bin/env bash
set -euo pipefail

# Start the Daedalus cockpit in development mode.
# Connects to the orchestrator at http://localhost:4000 by default.

cd "$(dirname "$0")/../cockpit"

if [ ! -d node_modules ]; then
  echo "[dev-cockpit] installing dependencies…"
  npm install
fi

echo "[dev-cockpit] starting Vite dev server"
exec npm run dev
