type NodePresence = {
  nodeId: string;
  label: string;
  platform: string;
  deviceType: string;
  operator: string;
  lastHeartbeatAt: string | null;
  lastJoinAt: string | null;
};

const nodes = new Map<string, NodePresence>();

export function recordHeartbeat(payload: {
  nodeId: string;
  label: string;
  platform: string;
  deviceType: string;
  operator: string;
  timestamp: string;
}) {
  const existing = nodes.get(payload.nodeId);
  const next: NodePresence = {
    nodeId: payload.nodeId,
    label: payload.label,
    platform: payload.platform,
    deviceType: payload.deviceType,
    operator: payload.operator,
    lastHeartbeatAt: payload.timestamp,
    lastJoinAt: existing?.lastJoinAt ?? null
  };
  nodes.set(payload.nodeId, next);
  return next;
}

export function recordJoin(payload: {
  nodeId: string;
  label: string;
  platform: string;
  deviceType: string;
  operator: string;
  requestedAt: string;
}) {
  const existing = nodes.get(payload.nodeId);
  const next: NodePresence = {
    nodeId: payload.nodeId,
    label: payload.label,
    platform: payload.platform,
    deviceType: payload.deviceType,
    operator: payload.operator,
    lastHeartbeatAt: existing?.lastHeartbeatAt ?? null,
    lastJoinAt: payload.requestedAt
  };
  nodes.set(payload.nodeId, next);
  return next;
}

export function listNodes() {
  return Array.from(nodes.values());
}
