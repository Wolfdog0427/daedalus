import {
  evaluateJoinProposal,
  applyJoinDecision,
  shouldRepropose,
  canNodePerformPrivilegedAction,
  createContinuityBinding,
} from '../../shared/daedalus/nodeNegotiationEngine';
import {
  NodeKind,
  NodeStatus,
  JoinDecisionKind,
  NodeJoinProposal,
  DeviceFingerprint,
  MOBILE_CAPABILITIES,
} from '../../shared/daedalus/nodeContracts';

const fp: DeviceFingerprint = {
  model: 'S26 Ultra',
  os: 'android',
  osVersion: '15',
  deviceId: 'dev-001',
};

function mkProposal(overrides: Partial<NodeJoinProposal> = {}): NodeJoinProposal {
  return {
    nodeId: 'n1',
    kind: NodeKind.MOBILE,
    capabilities: MOBILE_CAPABILITIES,
    fingerprint: fp,
    operatorId: 'op1',
    initialRiskSignals: [],
    proposedAt: Date.now(),
    ...overrides,
  };
}

describe('evaluateJoinProposal', () => {
  test('approves known device with matching fingerprint', () => {
    const decision = evaluateJoinProposal(mkProposal(), [fp]);
    expect(decision.decision).toBe(JoinDecisionKind.APPROVED);
  });

  test('needs approval for unknown fingerprint', () => {
    const decision = evaluateJoinProposal(mkProposal(), []);
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
  });

  test('needs approval when fingerprint drifted', () => {
    const drifted = { ...fp, osVersion: '14' };
    const decision = evaluateJoinProposal(mkProposal(), [drifted]);
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
  });

  test('needs approval for high risk signals', () => {
    const proposal = mkProposal({ initialRiskSignals: ['a', 'b', 'c'] });
    const decision = evaluateJoinProposal(proposal, [fp]);
    expect(decision.decision).toBe(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
  });

  test('rejects node without negotiation capability', () => {
    const proposal = mkProposal({
      capabilities: { ...MOBILE_CAPABILITIES, canNegotiate: false },
    });
    const decision = evaluateJoinProposal(proposal, [fp]);
    expect(decision.decision).toBe(JoinDecisionKind.REJECTED);
  });

  test('decision is frozen', () => {
    const decision = evaluateJoinProposal(mkProposal(), [fp]);
    expect(Object.isFrozen(decision)).toBe(true);
  });
});

describe('applyJoinDecision', () => {
  test('APPROVED → ACTIVE', () => {
    expect(applyJoinDecision(NodeStatus.PENDING, {
      nodeId: 'n1', decision: JoinDecisionKind.APPROVED, reason: '', decidedAt: 0,
    })).toBe(NodeStatus.ACTIVE);
  });

  test('REJECTED → DETACHED', () => {
    expect(applyJoinDecision(NodeStatus.PENDING, {
      nodeId: 'n1', decision: JoinDecisionKind.REJECTED, reason: '', decidedAt: 0,
    })).toBe(NodeStatus.DETACHED);
  });

  test('NEEDS_OPERATOR_APPROVAL → PENDING', () => {
    expect(applyJoinDecision(NodeStatus.PENDING, {
      nodeId: 'n1', decision: JoinDecisionKind.NEEDS_OPERATOR_APPROVAL, reason: '', decidedAt: 0,
    })).toBe(NodeStatus.PENDING);
  });
});

describe('shouldRepropose', () => {
  test('true when no binding', () => {
    expect(shouldRepropose(null, fp, [fp])).toBe(true);
  });

  test('true when fingerprint unknown', () => {
    const binding = createContinuityBinding('op1', 'n1', 'default');
    expect(shouldRepropose(binding, fp, [])).toBe(true);
  });

  test('true when fingerprint drifted', () => {
    const binding = createContinuityBinding('op1', 'n1', 'default');
    const drifted = { ...fp, osVersion: '14' };
    expect(shouldRepropose(binding, fp, [drifted])).toBe(true);
  });

  test('false when fingerprint matches', () => {
    const binding = createContinuityBinding('op1', 'n1', 'default');
    expect(shouldRepropose(binding, fp, [fp])).toBe(false);
  });
});

describe('canNodePerformPrivilegedAction', () => {
  test('true for ACTIVE', () => expect(canNodePerformPrivilegedAction(NodeStatus.ACTIVE)).toBe(true));
  test('false for PENDING', () => expect(canNodePerformPrivilegedAction(NodeStatus.PENDING)).toBe(false));
  test('false for QUARANTINED', () => expect(canNodePerformPrivilegedAction(NodeStatus.QUARANTINED)).toBe(false));
  test('false for DETACHED', () => expect(canNodePerformPrivilegedAction(NodeStatus.DETACHED)).toBe(false));
});
