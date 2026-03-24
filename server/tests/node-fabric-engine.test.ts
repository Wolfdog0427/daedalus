import {
  createEmptyRegistry,
  registerJoinProposal,
  resolveDecision,
  updateHeartbeat,
  updatePhysiology,
  quarantineNode,
  detachNode,
  listNodesForOperator,
  getNodeDetail,
  isNodeActive,
  canNodeAct,
} from '../../shared/daedalus/nodeFabricEngine';
import {
  NodeKind,
  NodeStatus,
  NodeRiskTier,
  JoinDecisionKind,
  NodeJoinProposal,
  NodeJoinDecision,
  NodeHealthSnapshot,
  NodePhysiologyState,
  MOBILE_CAPABILITIES,
  NODE_HEALTH_IDLE,
  NODE_PHYSIOLOGY_IDLE,
} from '../../shared/daedalus/nodeContracts';

const fp = { model: 'S26', os: 'android', osVersion: '15', deviceId: 'dev-1' };

function mkProposal(nodeId = 'n1'): NodeJoinProposal {
  return {
    nodeId,
    kind: NodeKind.MOBILE,
    capabilities: MOBILE_CAPABILITIES,
    fingerprint: fp,
    operatorId: 'op1',
    initialRiskSignals: [],
    proposedAt: Date.now(),
  };
}

function mkDecision(nodeId = 'n1', decision = JoinDecisionKind.APPROVED): NodeJoinDecision {
  return { nodeId, decision, reason: 'test', decidedAt: Date.now() };
}

describe('createEmptyRegistry', () => {
  test('starts empty', () => {
    const reg = createEmptyRegistry();
    expect(Object.keys(reg.nodes)).toHaveLength(0);
  });
});

describe('registerJoinProposal', () => {
  test('adds node with ACTIVE status on APPROVED', () => {
    const reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    expect(reg.nodes['n1'].status).toBe(NodeStatus.ACTIVE);
  });

  test('adds node with PENDING status on NEEDS_OPERATOR_APPROVAL', () => {
    const reg = registerJoinProposal(
      createEmptyRegistry(),
      mkProposal(),
      mkDecision('n1', JoinDecisionKind.NEEDS_OPERATOR_APPROVAL),
    );
    expect(reg.nodes['n1'].status).toBe(NodeStatus.PENDING);
  });

  test('adds node with DETACHED status on REJECTED', () => {
    const reg = registerJoinProposal(
      createEmptyRegistry(),
      mkProposal(),
      mkDecision('n1', JoinDecisionKind.REJECTED),
    );
    expect(reg.nodes['n1'].status).toBe(NodeStatus.DETACHED);
  });

  test('records join decision in history', () => {
    const d = mkDecision();
    const reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), d);
    expect(reg.nodes['n1'].joinHistory).toHaveLength(1);
    expect(reg.nodes['n1'].joinHistory[0]).toBe(d);
  });

  test('risk tier set based on signals', () => {
    const proposal = { ...mkProposal(), initialRiskSignals: ['a', 'b', 'c'] };
    const reg = registerJoinProposal(createEmptyRegistry(), proposal, mkDecision());
    expect(reg.nodes['n1'].riskTier).toBe(NodeRiskTier.HIGH);
  });
});

describe('resolveDecision', () => {
  test('approves pending node', () => {
    let reg = registerJoinProposal(
      createEmptyRegistry(),
      mkProposal(),
      mkDecision('n1', JoinDecisionKind.NEEDS_OPERATOR_APPROVAL),
    );
    reg = resolveDecision(reg, 'n1', mkDecision('n1', JoinDecisionKind.APPROVED));
    expect(reg.nodes['n1'].status).toBe(NodeStatus.ACTIVE);
    expect(reg.nodes['n1'].joinHistory).toHaveLength(2);
  });

  test('no-op for unknown node', () => {
    const reg = resolveDecision(createEmptyRegistry(), 'unknown', mkDecision('unknown'));
    expect(Object.keys(reg.nodes)).toHaveLength(0);
  });
});

describe('updateHeartbeat', () => {
  test('updates health snapshot', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    const health: NodeHealthSnapshot = {
      ...NODE_HEALTH_IDLE,
      nodeId: 'n1',
      liveness: true,
      batteryBand: 'MEDIUM',
      connectivityBand: 'MODERATE',
      degraded: false,
      timestamp: Date.now(),
    };
    reg = updateHeartbeat(reg, 'n1', health);
    expect(reg.nodes['n1'].health.batteryBand).toBe('MEDIUM');
  });

  test('marks DEGRADED when heartbeat degraded', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    const health: NodeHealthSnapshot = {
      ...NODE_HEALTH_IDLE,
      nodeId: 'n1',
      liveness: true,
      degraded: true,
      timestamp: Date.now(),
    };
    reg = updateHeartbeat(reg, 'n1', health);
    expect(reg.nodes['n1'].status).toBe(NodeStatus.DEGRADED);
  });

  test('recovers from DEGRADED to ACTIVE', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    const degraded: NodeHealthSnapshot = { ...NODE_HEALTH_IDLE, nodeId: 'n1', liveness: true, degraded: true, timestamp: Date.now() };
    reg = updateHeartbeat(reg, 'n1', degraded);
    const recovered: NodeHealthSnapshot = { ...NODE_HEALTH_IDLE, nodeId: 'n1', liveness: true, degraded: false, timestamp: Date.now() };
    reg = updateHeartbeat(reg, 'n1', recovered);
    expect(reg.nodes['n1'].status).toBe(NodeStatus.ACTIVE);
  });

  test('ignores heartbeat for DETACHED node', () => {
    let reg = registerJoinProposal(
      createEmptyRegistry(),
      mkProposal(),
      mkDecision('n1', JoinDecisionKind.REJECTED),
    );
    const health: NodeHealthSnapshot = { ...NODE_HEALTH_IDLE, nodeId: 'n1', liveness: true, timestamp: Date.now() };
    reg = updateHeartbeat(reg, 'n1', health);
    expect(reg.nodes['n1'].status).toBe(NodeStatus.DETACHED);
  });
});

describe('quarantineNode + detachNode', () => {
  test('quarantine sets status and risk tier', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    reg = quarantineNode(reg, 'n1');
    expect(reg.nodes['n1'].status).toBe(NodeStatus.QUARANTINED);
    expect(reg.nodes['n1'].riskTier).toBe(NodeRiskTier.QUARANTINED);
  });

  test('detach sets status to DETACHED', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    reg = detachNode(reg, 'n1');
    expect(reg.nodes['n1'].status).toBe(NodeStatus.DETACHED);
  });
});

describe('listNodesForOperator', () => {
  test('returns nodes for operator', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal('a'), mkDecision('a'));
    reg = registerJoinProposal(reg, { ...mkProposal('b'), operatorId: 'other' }, mkDecision('b'));
    expect(listNodesForOperator(reg, 'op1')).toHaveLength(1);
    expect(listNodesForOperator(reg, 'other')).toHaveLength(1);
  });
});

describe('getNodeDetail', () => {
  test('returns detail for existing node', () => {
    const reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    const detail = getNodeDetail(reg, 'n1');
    expect(detail).not.toBeNull();
    expect(detail!.nodeId).toBe('n1');
  });

  test('returns null for unknown node', () => {
    expect(getNodeDetail(createEmptyRegistry(), 'x')).toBeNull();
  });
});

describe('isNodeActive + canNodeAct', () => {
  test('active node can act', () => {
    const reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    expect(isNodeActive(reg, 'n1')).toBe(true);
    expect(canNodeAct(reg, 'n1')).toBe(true);
  });

  test('quarantined node cannot act', () => {
    let reg = registerJoinProposal(createEmptyRegistry(), mkProposal(), mkDecision());
    reg = quarantineNode(reg, 'n1');
    expect(isNodeActive(reg, 'n1')).toBe(false);
    expect(canNodeAct(reg, 'n1')).toBe(false);
  });
});
