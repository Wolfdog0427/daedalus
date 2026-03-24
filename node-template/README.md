# Daedalus Node Template

Canonical template for creating sovereign Daedalus nodes. Every node — mobile,
desktop, server, embedded — is generated from this template and inherits the
full lifecycle, invariants, physiology, and continuity wiring.

## Architecture

```
node-template/
├── src/
│   ├── contracts.ts          Re-exports shared types + template interfaces
│   ├── transport.ts          NodeTransport interface (network abstraction)
│   ├── deviceAdapter.ts      DeviceAdapter interface (platform abstraction)
│   ├── heartbeatEngine.ts    Stateful heartbeat with cadence + degraded mode
│   ├── joinNegotiator.ts     Join protocol with invariant enforcement
│   ├── physiologyDriver.ts   Posture / glow / comfort mapping
│   ├── runtime.ts            createNodeRuntime() — wires everything
│   ├── lifecycle/
│   │   └── stateMachine.ts   Validated state transitions
│   ├── invariants/
│   │   └── invariants.ts     No silent joins, operator sovereignty
│   └── adapters/
│       ├── mobile.ts         Mobile device adapter
│       ├── desktop.ts        Desktop device adapter
│       └── server.ts         Server device adapter
├── tests/                    Full test coverage
├── scripts/
│   └── generate-node.js      Scaffolding command
└── README.md
```

## Lifecycle States

```
PENDING → ACTIVE → DEGRADED → QUARANTINED → DETACHED
                 ↗            ↗              ↗
          PENDING → DETACHED (rejected)
```

- **PENDING** — Join proposed, awaiting decision.
- **ACTIVE** — Approved and heartbeating.
- **DEGRADED** — Heartbeat degraded (weak connectivity, critical battery).
- **QUARANTINED** — Isolated by operator or system.
- **DETACHED** — Removed from fabric.

## Invariants

- **No silent joins** — `ACTIVE` requires an `APPROVED` decision.
- **Operator sovereignty** — Privileged actions require operator approval.
- **No quarantined actions** — Quarantined nodes cannot act.
- **Fingerprint fidelity** — Changed fingerprint forces re-proposal.

## Usage

### Create a node runtime

```typescript
import { createNodeRuntime, createMobileAdapter, NodeKind, MOBILE_CAPABILITIES } from './index';

const device = createMobileAdapter({
  deviceId: 'dev-001',
  model: 'S26 Ultra',
  os: 'android',
  osVersion: '15',
});

const runtime = createNodeRuntime(
  {
    nodeId: 'node-s26-01',
    kind: NodeKind.MOBILE,
    capabilities: MOBILE_CAPABILITIES,
    operatorId: 'wolfdog',
    trustDomain: 'default',
    baseCadenceMs: 15000,
    degradedCadenceMs: 5000,
  },
  myTransport,
  device,
);

await runtime.start();
```

### Generate a new node package

```bash
node node-template/scripts/generate-node.js my-new-node
```

## Testing

```bash
cd node-template
npm install
npm test
```

## Shared Contracts

All types are imported from `shared/daedalus/nodeContracts.ts`. The template
never duplicates or forks these — it re-exports them through `src/contracts.ts`
and adds template-specific interfaces (`NodeTemplateConfig`, `NodeRuntime`,
`ContinuitySignals`).
