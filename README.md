# Daedalus

A distributed, expressive AI orchestration system with governance, continuity tracking, and real-time cockpit visibility.

## Architecture

```
daedalus/
├── server/           # Orchestrator (Express + TypeScript)
├── cockpit/          # Operator UI (React 19 + Vite)
├── node-agent/       # Reusable node agent library
├── shared/daedalus/  # Shared contracts, types, engines
├── daedalus-node-mobile/  # Mobile node (Expo React Native)
└── tests/multinode/  # Multi-node test harness
```

**Orchestrator** — central nervous system. Manages node mirrors, governance posture, being ontology, continuity tracking, and persistence.

**Cockpit** — sensory cortex. Real-time UI for operators showing nodes, governance, constitution status, and recommended actions.

**Node Agent** — reusable library that any node (mobile, desktop, server, embedded) uses to join, heartbeat, sync capabilities, and report expressive state.

**Shared Contracts** — canonical type definitions, expressive engines, behavioral grammar, continuity narrator, and being constitution.

## Quick Start

### Prerequisites

- Node.js 18+
- npm 9+

### 1. Clone and install

```bash
git clone <repo-url> daedalus
cd daedalus

# Install server dependencies
cd server && npm install && cd ..

# Install cockpit dependencies
cd cockpit && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to set DAEDALUS_TOKEN for production use
```

### 3. Start the orchestrator

```bash
cd server
npm start
# Listens on http://0.0.0.0:3001 by default
```

### 4. Start the cockpit

```bash
cd cockpit
npm run dev
# Opens http://localhost:5173, proxies /daedalus/* to the orchestrator
```

### 5. (Optional) Start the mobile node

```bash
cd daedalus-node-mobile
npm install
npm start
# Expo dev server — scan QR with Expo Go
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DAEDALUS_PORT` | `3001` | Orchestrator listen port |
| `DAEDALUS_HOST` | `0.0.0.0` | Orchestrator bind address |
| `DAEDALUS_TOKEN` | `daedalus-dev-token` | Auth token for API access |
| `DAEDALUS_CORS_ORIGINS` | *(allow all)* | Comma-separated allowed origins |
| `VITE_ORCHESTRATOR_URL` | `http://localhost:3001` | Cockpit proxy target |
| `VITE_DAEDALUS_TOKEN` | `daedalus-dev-token` | Cockpit auth token |

## API Endpoints

All endpoints under `/daedalus` require the auth token via `x-daedalus-token` header, `Authorization: Bearer <token>`, or `?token=` query param. Rate-limited to 300 req/min per IP.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (no auth) |
| GET | `/daedalus/snapshot` | Full orchestrator snapshot |
| GET | `/daedalus/cockpit/nodes` | Node list for cockpit |
| GET | `/daedalus/cockpit/summary` | Summary with urgency and recommended actions |
| GET | `/daedalus/governance/posture` | Current governance posture |
| POST | `/daedalus/governance/overrides` | Create override (supports `expiresAt` for TTL) |
| DELETE | `/daedalus/governance/overrides` | Clear all overrides |
| POST | `/daedalus/governance/drifts` | Record drift (supports `expiresAt` for TTL) |
| DELETE | `/daedalus/governance/drifts` | Clear all drifts |
| POST | `/daedalus/governance/votes` | Cast being vote |
| DELETE | `/daedalus/governance/votes` | Clear all votes |
| POST | `/daedalus/mirror/join` | Node join |
| POST | `/daedalus/mirror/heartbeat` | Node heartbeat |
| GET | `/daedalus/events` | SSE event stream |
| GET | `/daedalus/events/history` | Event history (query: `limit`, `type`) |
| GET | `/daedalus/constitution` | Being constitution report |
| GET | `/daedalus/incidents` | List incidents (query: `status`) |
| POST | `/daedalus/incidents` | Open incident (`title`, `severity`, `notes?`) |
| PATCH | `/daedalus/incidents/:id` | Update incident |
| POST | `/daedalus/incidents/:id/resolve` | Resolve incident |
| GET | `/daedalus/actions` | Action log (query: `limit`) |
| POST | `/daedalus/actions/:id/undo` | Undo an action |

## Running Tests

```bash
cd server
npm test
```

This runs the full suite: unit tests, integration tests, governance, continuity, being constitution, chaos, load, adversarial, red-team security, schema migration, operator UX, long-horizon risk analysis, and endurance runs.

## Graceful Shutdown

The orchestrator handles `SIGTERM` and `SIGINT` by saving a final snapshot before exiting, ensuring no state loss on deployment or restart.

## Persistence

State is persisted to `.daedalus-snapshot.json` in the server working directory. Auto-saves every 30 seconds and on graceful shutdown. Restored automatically on startup. Includes beings, governance state, mirrors, and event history.

## Rate Limiting

All `/daedalus/*` endpoints are rate-limited to 300 requests per minute per IP. Returns `429 Too Many Requests` with `retryAfterMs` when exceeded. Bypassed in test environment.

## Override/Drift TTL

Overrides and drifts support an optional `expiresAt` ISO timestamp. Expired entries are swept automatically every 30 seconds (on the auto-save cycle). Governance posture recomputes after sweep.

## Incidents

Operators can open, update, and resolve incidents via the API or cockpit UI. Incidents are tracked with severity (LOW/MEDIUM/HIGH/CRITICAL) and status (open/investigating/mitigated/resolved).

## Action Log & Undo

Every governance action (create override, record drift, open incident, etc.) is recorded in an action log. Undoable actions (like creating an override) can be reversed via `POST /daedalus/actions/:id/undo`.

## Structured Logging

When `DAEDALUS_LOG_FILE=true` is set, logs are written to `daedalus.log` with automatic rotation at 10MB (up to 5 rotated files). Logs are structured JSON for easy parsing.

## Monorepo

This project uses npm workspaces. From the root:

```bash
npm install          # installs all workspaces
npm start            # starts the orchestrator
npm run dev:cockpit  # starts the cockpit dev server
npm test             # runs server tests
```
