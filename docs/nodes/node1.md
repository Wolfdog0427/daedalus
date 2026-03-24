# Node 1 — First Sovereign Mobile Node

Node 1 is the first mobile device to join the Daedalus fabric.
It establishes the pattern for all future nodes: join negotiation,
heartbeat, expressive physiology, operator notification, and
continuity binding.

## Role

Node 1 is a sovereign mobile node (S26 Ultra) that:

- Proposes a join to the continuity fabric
- Receives a decision (approved, rejected, or needs operator approval)
- Emits periodic heartbeats with health snapshots
- Maintains an expressive physiology state derived from health and risk
- Appears in the cockpit node fabric panel
- Generates operator notifications for key lifecycle events

## Join Lifecycle

1. **Propose** — Node sends a `NodeJoinProposal` with identity, capabilities, device fingerprint, and risk signals.
2. **Security gate** — The fabric evaluates fingerprint match, network trust, and anomaly history.
3. **Decision** — One of:
   - `APPROVED` → Node becomes `ACTIVE`.
   - `REJECTED` → Node becomes `DETACHED`.
   - `NEEDS_OPERATOR_APPROVAL` → Node stays `PENDING`; operator is notified.
4. **Operator action** — For pending nodes, the operator approves, rejects, quarantines, or detaches via the cockpit.
5. **Continuity binding** — On approval, a binding is created linking the node to the operator's trust domain.

## Heartbeat

- Base cadence: 15 seconds.
- Degraded cadence: 5 seconds (when connectivity or battery is critical).
- Each heartbeat emits a `NodeHealthSnapshot` with liveness, battery band, connectivity band, anomaly summary, and degraded flag.
- Degraded heartbeats transition the node to `DEGRADED` status; recovery returns it to `ACTIVE`.

## Physiology Mapping

| Health / Risk | Posture | Glow | Motion |
|---|---|---|---|
| Healthy + LOW risk | CALM | Blue, 0.6 | Breathe |
| Healthy + MEDIUM/HIGH risk | ALERT | Gold, 0.8 | Pulse |
| QUARANTINED | DEFENSIVE | Red, 0.9 | Flicker |
| Degraded heartbeat | DEGRADED | Grey, 0.3 | Steady |
| Offline | DEGRADED | Grey, 0.1 | Steady |

Comfort flags surface specific concerns: `LOW_BATTERY`, `UNSTABLE_NETWORK`, `HIGH_RISK_CONTEXT`, `QUARANTINE_RISK`.

## Operator Controls

From the cockpit Node Fabric panel, the operator can:

- **Approve** — Accept a pending join request.
- **Reject** — Deny a pending join request.
- **Quarantine** — Isolate an active or degraded node.
- **Detach** — Remove a node from the fabric.

## Notifications

| Event | Type | When |
|---|---|---|
| New join proposal needs approval | `NODE_JOIN_REQUEST` | Unknown fingerprint or high risk signals |
| Risk tier increases | `NODE_RISK_ESCALATION` | Risk moves from LOW to MEDIUM/HIGH |
| Sustained degraded heartbeat | `NODE_DEGRADED` | Heartbeat enters degraded band |
| Node quarantined | `NODE_QUARANTINE` | Operator or system quarantines node |
| Node detached | `NODE_DETACH_CONFIRMATION` | Node removed from fabric |

All notifications are logged for audit and continuity history.

## Invariants

- No node can be `ACTIVE` without an `APPROVED` decision.
- Any change in device fingerprint forces a new join proposal.
- Quarantined nodes cannot perform privileged actions.
- All major state changes are surfaced to the operator.
- Node 1 is the first instance of a general node pattern; all contracts are reusable.
