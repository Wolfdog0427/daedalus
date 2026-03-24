import {
  NodeKind,
  NodeStatus,
  NodeRiskTier,
  JoinDecisionKind,
  NodeJoinProposal,
  MOBILE_CAPABILITIES,
  NODE_HEALTH_IDLE,
} from '../../shared/daedalus/nodeContracts';
import {
  createEmptyRegistry,
  registerJoinProposal,
  resolveDecision,
  updateHeartbeat,
  updatePhysiology,
  quarantineNode,
  getNodeDetail,
} from '../../shared/daedalus/nodeFabricEngine';
import { evaluateJoinProposal } from '../../shared/daedalus/nodeNegotiationEngine';
import { computeHeartbeatSnapshot, HeartbeatConfig } from '../../shared/daedalus/nodeHeartbeatEngine';
import { computePhysiologyState } from '../../shared/daedalus/nodePhysiologyEngine';
import { securityGateJoinProposal } from '../../shared/daedalus/nodeSecurityEngine';
import {
  createJoinRequestNotification,
  createDegradedNotification,
  createQuarantineNotification,
} from '../../shared/daedalus/nodeNotificationEngine';

const fp = { model: 'S26 Ultra', os: 'android', osVersion: '15', deviceId: 'node1-dev' };

const proposal: NodeJoinProposal = {
  nodeId: 'node-1',
  kind: NodeKind.MOBILE,
  capabilities: MOBILE_CAPABILITIES,
  fingerprint: fp,
  operatorId: 'wolfdog',
  initialRiskSignals: [],
  proposedAt: Date.now(),
};

const hbConfig: HeartbeatConfig = {
  nodeId: 'node-1',
  baseCadenceMs: 15000,
  degradedCadenceMs: 5000,
  degradedThreshold: 3,
};

describe('Node 1 integration: APPROVED flow', () => {
  test('known device auto-approves and reaches ACTIVE', () => {
    const decision = evaluateJoinProposal(proposal, [fp]);
    expect(decision.decision).toBe(JoinDecisionKind.APPROVED);

    const reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);
    const detail = getNodeDetail(reg, 'node-1');
    expect(detail!.status).toBe(NodeStatus.ACTIVE);
    expect(detail!.kind).toBe(NodeKind.MOBILE);
  });

  test('heartbeat updates health in registry', () => {
    const decision = evaluateJoinProposal(proposal, [fp]);
    let reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);

    const snap = computeHeartbeatSnapshot(hbConfig, {
      batteryLevel: 0.7,
      networkStrength: 0.9,
      anomalies: [],
    });
    reg = updateHeartbeat(reg, 'node-1', snap);
    expect(reg.nodes['node-1'].health.batteryBand).toBe('HIGH');
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.ACTIVE);
  });

  test('physiology reflects health and risk', () => {
    const decision = evaluateJoinProposal(proposal, [fp]);
    let reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);

    const snap = computeHeartbeatSnapshot(hbConfig, {
      batteryLevel: 0.7,
      networkStrength: 0.9,
      anomalies: [],
    });
    reg = updateHeartbeat(reg, 'node-1', snap);

    const physiology = computePhysiologyState('node-1', {
      health: snap,
      riskTier: NodeRiskTier.LOW,
      operatorAttention: 0.6,
      emotionalTrajectory: 'stable',
    });
    reg = updatePhysiology(reg, 'node-1', physiology);
    expect(reg.nodes['node-1'].physiology.posture).toBe('CALM');
  });
});

describe('Node 1 integration: NEEDS_OPERATOR_APPROVAL flow', () => {
  test('unknown device requires approval, then operator approves', () => {
    const decision = evaluateJoinProposal(proposal, []);
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);

    let reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.PENDING);

    const notif = createJoinRequestNotification(proposal);
    expect(notif.type).toBe('NODE_JOIN_REQUEST');

    const approval = {
      nodeId: 'node-1' as string,
      decision: JoinDecisionKind.APPROVED,
      reason: 'Operator verified device',
      decidedAt: Date.now(),
    };
    reg = resolveDecision(reg, 'node-1', approval);
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.ACTIVE);
  });
});

describe('Node 1 integration: REJECTED flow', () => {
  test('rejected node becomes DETACHED', () => {
    const rejection = {
      nodeId: 'node-1' as string,
      decision: JoinDecisionKind.REJECTED,
      reason: 'Operator rejected',
      decidedAt: Date.now(),
    };
    const reg = registerJoinProposal(createEmptyRegistry(), proposal, rejection);
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.DETACHED);
  });
});

describe('Node 1 integration: degradation and quarantine', () => {
  test('degraded heartbeat transitions to DEGRADED, then recovers', () => {
    const decision = evaluateJoinProposal(proposal, [fp]);
    let reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);

    const degradedSnap = computeHeartbeatSnapshot(hbConfig, {
      batteryLevel: 0.05,
      networkStrength: 0.1,
      anomalies: ['battery critical'],
    });
    reg = updateHeartbeat(reg, 'node-1', degradedSnap);
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.DEGRADED);

    const degradedNotif = createDegradedNotification('node-1', 'S26 Ultra', degradedSnap.anomalySummary);
    expect(degradedNotif.type).toBe('NODE_DEGRADED');

    const recoveredSnap = computeHeartbeatSnapshot(hbConfig, {
      batteryLevel: 0.8,
      networkStrength: 0.9,
      anomalies: [],
    });
    reg = updateHeartbeat(reg, 'node-1', recoveredSnap);
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.ACTIVE);
  });

  test('quarantine sets QUARANTINED status and risk tier', () => {
    const decision = evaluateJoinProposal(proposal, [fp]);
    let reg = registerJoinProposal(createEmptyRegistry(), proposal, decision);

    reg = quarantineNode(reg, 'node-1');
    expect(reg.nodes['node-1'].status).toBe(NodeStatus.QUARANTINED);
    expect(reg.nodes['node-1'].riskTier).toBe(NodeRiskTier.QUARANTINED);

    const notif = createQuarantineNotification('node-1', 'S26 Ultra', 'Operator action');
    expect(notif.type).toBe('NODE_QUARANTINE');
  });
});

describe('Node 1 integration: security gate', () => {
  test('trusted known device passes security gate', () => {
    const decision = securityGateJoinProposal(proposal, {
      knownFingerprints: [fp],
      recentAnomalies: [],
      networkTrust: 'trusted',
    });
    expect(decision.decision).toBe(JoinDecisionKind.APPROVED);
  });

  test('untrusted network requires operator approval', () => {
    const decision = securityGateJoinProposal(proposal, {
      knownFingerprints: [fp],
      recentAnomalies: [],
      networkTrust: 'untrusted',
    });
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
  });

  test('unknown device requires operator approval', () => {
    const decision = securityGateJoinProposal(proposal, {
      knownFingerprints: [],
      recentAnomalies: [],
      networkTrust: 'trusted',
    });
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
  });
});
