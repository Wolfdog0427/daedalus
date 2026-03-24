# Daedalus Developer Guide

## Prerequisites

- Node.js v20+ (v24 recommended)
- npm

## Running the orchestrator

```bash
cd orchestrator
npm install
npm run dev
```

The orchestrator starts on port 4000 by default. Override with:

```bash
ORCHESTRATOR_PORT=5000 npm run dev
```

## Running the cockpit

```bash
cd cockpit
npm install
npm run dev
```

The cockpit starts on Vite's default port (5173). It connects to the orchestrator at `http://localhost:4000` by default. Override with a `.env` file:

```
VITE_ORCHESTRATOR_URL=http://localhost:5000
```

## Running both

```bash
# From the workspace root:
bash scripts/dev-all.sh
```

## Inspecting the system

### Health

```bash
curl http://localhost:4000/health
```

Returns status, version, posture mode, and current risk tier.

### Node registry

```bash
curl http://localhost:4000/nodes
```

Returns all registered nodes with capabilities and heartbeat timestamps.

To register a test node:

```bash
curl -X POST http://localhost:4000/events \
  -H "Content-Type: application/json" \
  -d '{"type":"node.joined","payload":{"id":"test-node","capabilities":["echo","shard"]}}'
```

### Risk & verification

```bash
curl http://localhost:4000/risk
```

Returns the current risk tier, contributing factors, verification requirement, and last verification event.

### Continuity timeline

```bash
curl http://localhost:4000/continuity/timeline
```

Returns recent pipeline events with summaries and thread grouping.

### Full state

```bash
curl http://localhost:4000/state
```

Returns the complete orchestrator state including all engine snapshots.

## Running tests

```bash
cd orchestrator
npm test
```

Runs the test suite for presence, risk, verification, and continuity engines.

## Architecture

See [v0.3 overview](./v03-overview.md) for the full architecture description.
