# Daedalus v0.3 Overview

Daedalus v0.3 extends the orchestrator with three new subsystems and surfaces them in the cockpit. All changes are additive — the v0.2 pipeline, engines, and HTTP contract remain intact.

## New subsystems

### Node Registry (Phase 1)

The **PresenceEngine** now maintains a typed node registry. Nodes register via `node.joined` events and maintain presence through `node.heartbeat` events. Each node descriptor includes an ID, capability list, last heartbeat timestamp, and optional metadata.

- **Endpoint**: `GET /nodes` returns the full registry snapshot with node count.
- **Cockpit**: NodesPanel displays registered nodes, their capabilities, and last-seen times.

### Risk & Verification (Phase 2)

A **RiskEngine** classifies system risk into four tiers (`low`, `medium`, `elevated`, `critical`) based on posture mode, node count, and event volume. A **VerificationEngine** maps risk tiers to verification requirements (`none`, `soft`, `strong`) and tracks the last verification event.

Both engines run as pipeline stages after posture evaluation:
1. Posture → Risk assessment → Verification requirement

- **Endpoint**: `GET /risk` returns the risk snapshot and verification state.
- **Endpoint**: `/state` now includes `risk` and `verification` sections.
- **Cockpit**: RiskPanel shows the current tier, verification requirement, contributing factors, and last verification event.

### Continuity Timeline (Phase 3)

The **ContinuityEngine** now records a timeline of all processed events with human-readable summaries. The timeline is capped at 200 entries and groups events by thread ID.

- **Endpoint**: `GET /continuity/timeline` returns timeline entries and active thread IDs.
- **Cockpit**: ContinuityTimelinePanel renders the timeline in reverse chronological order, highlighting posture shifts.

## Pipeline stages (v0.3)

The event pipeline now has seven stages:

1. **Presence** — register/track nodes, beings, sessions
2. **Continuity** — update threads, record timeline entry
3. **Posture** — evaluate posture transitions
4. **Risk** — classify risk tier
5. **Verification** — update verification requirement
6. **State** — persist event to state store
7. **Publish** — emit processed event to subscribers

## HTTP endpoints

| Method | Path                   | Description                        |
|--------|------------------------|------------------------------------|
| GET    | /health                | Status, version, posture, risk     |
| GET    | /state                 | Full state + all engine snapshots   |
| GET    | /nodes                 | Node registry snapshot             |
| GET    | /risk                  | Risk + verification snapshot       |
| GET    | /continuity/timeline   | Continuity timeline                |
| GET    | /context               | System + operator context          |
| POST   | /events                | Submit an event to the pipeline    |
| POST   | /commands              | Dispatch a command                 |
| GET    | /events/stream         | SSE stream of processed events     |

## Outer repos

- **shared/** — canonical domain types (Node, Risk, Verification, Timeline), constants, and placeholder schemas/manifests.
- **node/** — scaffold with runtime config types. Full activation in v0.4.
- **kernel/** — scaffold with being descriptor types. Full activation in v0.4+.
