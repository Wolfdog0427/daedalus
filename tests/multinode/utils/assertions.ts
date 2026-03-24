import { NodeHandle } from '../harness/NodeSpawner';
import { OrchestratorStub } from '../harness/OrchestratorStub';

export function assertNodeJoined(node: NodeHandle, orchestrator: OrchestratorStub): void {
  const mirror = orchestrator.getNode(node.id);
  if (!mirror) {
    throw new Error(`assertNodeJoined: node ${node.id} not found in orchestrator`);
  }
  if (mirror.status !== 'joining' && mirror.status !== 'online') {
    throw new Error(
      `assertNodeJoined: node ${node.id} has unexpected status ${mirror.status}`,
    );
  }
}

export function assertCapabilitiesSynced(node: NodeHandle, orchestrator: OrchestratorStub): void {
  const mirror = orchestrator.getNode(node.id);
  if (!mirror) {
    throw new Error(`assertCapabilitiesSynced: node ${node.id} not found in orchestrator`);
  }

  const nodeCaps = node.capabilities;
  const mirrorCaps = mirror.capabilities;

  for (const key of Object.keys(nodeCaps)) {
    if (mirrorCaps[key] !== nodeCaps[key]) {
      throw new Error(
        `assertCapabilitiesSynced: mismatch for ${key}: node=${nodeCaps[key]} mirror=${mirrorCaps[key]}`,
      );
    }
  }
}

export function assertExpressiveSynced(node: NodeHandle, orchestrator: OrchestratorStub): void {
  const mirror = orchestrator.getNode(node.id);
  if (!mirror) {
    throw new Error(`assertExpressiveSynced: node ${node.id} not found in orchestrator`);
  }

  const nodeExpr = node.expressive;
  const mirrorExpr = mirror.expressive;

  for (const key of Object.keys(nodeExpr)) {
    if (mirrorExpr[key] !== nodeExpr[key]) {
      throw new Error(
        `assertExpressiveSynced: mismatch for ${key}: node=${nodeExpr[key]} mirror=${mirrorExpr[key]}`,
      );
    }
  }
}

export function assertHeartbeatStable(node: NodeHandle): void {
  const heartbeats = node.events.entries.filter(e => e.type === 'heartbeat_sent');
  if (heartbeats.length === 0) {
    throw new Error(`assertHeartbeatStable: no heartbeats recorded for node ${node.id}`);
  }
}
