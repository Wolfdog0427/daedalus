import {
  NodeId,
  NodeKind,
  NodeStatus,
  NodeRiskTier,
  NodeCapabilities,
  NodeHealthSnapshot,
  NodePhysiologyState,
  NodeJoinProposal,
  NodeJoinDecision,
  JoinDecisionKind,
  NodeContinuityBinding,
  DeviceFingerprint,
  NodeSummary,
  NodeDetail,
  NODE_HEALTH_IDLE,
  NODE_PHYSIOLOGY_IDLE,
} from './nodeContracts';

export interface NodeRegistryEntry {
  readonly nodeId: NodeId;
  readonly kind: NodeKind;
  readonly capabilities: NodeCapabilities;
  readonly fingerprint: DeviceFingerprint;
  readonly operatorId: string;
  readonly status: NodeStatus;
  readonly riskTier: NodeRiskTier;
  readonly binding: NodeContinuityBinding | null;
  readonly health: NodeHealthSnapshot;
  readonly physiology: NodePhysiologyState;
  readonly joinHistory: readonly NodeJoinDecision[];
}

export interface NodeRegistry {
  readonly nodes: Record<NodeId, NodeRegistryEntry>;
}

export function createEmptyRegistry(): NodeRegistry {
  return Object.freeze({ nodes: {} });
}

export function registerJoinProposal(
  registry: NodeRegistry,
  proposal: NodeJoinProposal,
  decision: NodeJoinDecision,
): NodeRegistry {
  const status =
    decision.decision === JoinDecisionKind.APPROVED
      ? NodeStatus.ACTIVE
      : decision.decision === JoinDecisionKind.REJECTED
        ? NodeStatus.DETACHED
        : NodeStatus.PENDING;

  const entry: NodeRegistryEntry = Object.freeze({
    nodeId: proposal.nodeId,
    kind: proposal.kind,
    capabilities: proposal.capabilities,
    fingerprint: proposal.fingerprint,
    operatorId: proposal.operatorId,
    status,
    riskTier:
      proposal.initialRiskSignals.length > 2
        ? NodeRiskTier.HIGH
        : proposal.initialRiskSignals.length > 0
          ? NodeRiskTier.MEDIUM
          : NodeRiskTier.LOW,
    binding: null,
    health: Object.freeze({ ...NODE_HEALTH_IDLE, nodeId: proposal.nodeId }),
    physiology: Object.freeze({ ...NODE_PHYSIOLOGY_IDLE, nodeId: proposal.nodeId }),
    joinHistory: Object.freeze([decision]),
  });

  return Object.freeze({
    nodes: { ...registry.nodes, [proposal.nodeId]: entry },
  });
}

export function resolveDecision(
  registry: NodeRegistry,
  nodeId: NodeId,
  decision: NodeJoinDecision,
): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;

  const newStatus =
    decision.decision === JoinDecisionKind.APPROVED
      ? NodeStatus.ACTIVE
      : decision.decision === JoinDecisionKind.REJECTED
        ? NodeStatus.DETACHED
        : entry.status;

  const updated: NodeRegistryEntry = Object.freeze({
    ...entry,
    status: newStatus,
    joinHistory: Object.freeze([...entry.joinHistory, decision]),
  });

  return Object.freeze({
    nodes: { ...registry.nodes, [nodeId]: updated },
  });
}

export function updateHeartbeat(
  registry: NodeRegistry,
  nodeId: NodeId,
  health: NodeHealthSnapshot,
): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;
  if (entry.status === NodeStatus.DETACHED) return registry;

  const newStatus = health.degraded && entry.status === NodeStatus.ACTIVE
    ? NodeStatus.DEGRADED
    : !health.degraded && entry.status === NodeStatus.DEGRADED
      ? NodeStatus.ACTIVE
      : entry.status;

  const updated: NodeRegistryEntry = Object.freeze({
    ...entry,
    health,
    status: newStatus,
  });

  return Object.freeze({
    nodes: { ...registry.nodes, [nodeId]: updated },
  });
}

export function updatePhysiology(
  registry: NodeRegistry,
  nodeId: NodeId,
  physiology: NodePhysiologyState,
): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;

  const updated: NodeRegistryEntry = Object.freeze({
    ...entry,
    physiology,
  });

  return Object.freeze({
    nodes: { ...registry.nodes, [nodeId]: updated },
  });
}

export function updateBinding(
  registry: NodeRegistry,
  nodeId: NodeId,
  binding: NodeContinuityBinding,
): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;

  return Object.freeze({
    nodes: { ...registry.nodes, [nodeId]: Object.freeze({ ...entry, binding }) },
  });
}

export function quarantineNode(registry: NodeRegistry, nodeId: NodeId): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;

  return Object.freeze({
    nodes: {
      ...registry.nodes,
      [nodeId]: Object.freeze({
        ...entry,
        status: NodeStatus.QUARANTINED,
        riskTier: NodeRiskTier.QUARANTINED,
      }),
    },
  });
}

export function detachNode(registry: NodeRegistry, nodeId: NodeId): NodeRegistry {
  const entry = registry.nodes[nodeId];
  if (!entry) return registry;

  return Object.freeze({
    nodes: {
      ...registry.nodes,
      [nodeId]: Object.freeze({ ...entry, status: NodeStatus.DETACHED }),
    },
  });
}

export function listNodesForOperator(
  registry: NodeRegistry,
  operatorId: string,
): NodeSummary[] {
  return Object.values(registry.nodes)
    .filter(e => e.operatorId === operatorId)
    .map(e =>
      Object.freeze({
        nodeId: e.nodeId,
        kind: e.kind,
        status: e.status,
        riskTier: e.riskTier,
        batteryBand: e.health.batteryBand,
        connectivityBand: e.health.connectivityBand,
        posture: e.physiology.posture,
        lastHeartbeat: e.health.timestamp,
      }),
    );
}

export function getNodeDetail(
  registry: NodeRegistry,
  nodeId: NodeId,
): NodeDetail | null {
  const e = registry.nodes[nodeId];
  if (!e) return null;

  return Object.freeze({
    nodeId: e.nodeId,
    kind: e.kind,
    status: e.status,
    riskTier: e.riskTier,
    capabilities: e.capabilities,
    fingerprint: e.fingerprint,
    binding: e.binding,
    health: e.health,
    physiology: e.physiology,
    joinHistory: e.joinHistory,
  });
}

export function isNodeActive(registry: NodeRegistry, nodeId: NodeId): boolean {
  return registry.nodes[nodeId]?.status === NodeStatus.ACTIVE;
}

export function canNodeAct(registry: NodeRegistry, nodeId: NodeId): boolean {
  const entry = registry.nodes[nodeId];
  if (!entry) return false;
  return entry.status === NodeStatus.ACTIVE || entry.status === NodeStatus.DEGRADED;
}
