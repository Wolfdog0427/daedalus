# Daedalus Node Mobile

A Daedalus mobile node built with Expo React Native. Connects to the central orchestrator as a first-class node in the Daedalus fabric.

- **Identity:** configured in `src/config/identity.ts`
- **Heartbeat:** periodic POST to the orchestrator via `NodeAgent`
- **Continuity:** timestamps stored locally via AsyncStorage
- **Auth:** sends `x-daedalus-token` header (configured in `app.json` → `extra.daedalusToken`)

## Layout

- `App.tsx` — Daedalus node shell UI
- `src/config/identity.ts` — canonical identity for this node
- `src/services/heartbeat.ts` — heartbeat engine (direct HTTP)
- `src/services/presenceClient.ts` — full `NodeAgent`-backed presence client
- `src/services/continuity.ts` — continuity storage (AsyncStorage)
- `src/context/DaedalusContext.tsx` — wiring for identity, heartbeat, continuity, join

## Prerequisites

- The Daedalus orchestrator must be running (default: `http://localhost:3001`)
- For Android emulator, the orchestrator is reachable at `http://10.0.2.2:3001`
- Set orchestrator URL in `app.json` → `extra.orchestratorUrl`

## Quick Start

1. Install dependencies:

   ```bash
   cd daedalus-node-mobile
   npm install
   ```

2. Start the Expo app:

   ```bash
   npm start
   ```

3. Scan the QR code with Expo Go on your device.

## Configuration

Set these in `app.json` → `extra`:

| Key | Default | Description |
|---|---|---|
| `orchestratorUrl` | `http://10.0.2.2:3001` | Orchestrator base URL |
| `daedalusToken` | `daedalus-dev-token` | Auth token for API calls |
