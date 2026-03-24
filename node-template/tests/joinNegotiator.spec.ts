import { createJoinNegotiator } from '../src/joinNegotiator';
import { NodeLifecycle } from '../src/lifecycle/stateMachine';
import type { NodeTransport } from '../src/transport';
import {
  NodeStatus,
  NodeKind,
  JoinDecisionKind,
  NodeJoinProposal,
  NodeJoinDecision,
  MOBILE_CAPABILITIES,
  DeviceFingerprint,
} from '../../shared/daedalus/nodeContracts';
import { createContinuityBinding } from '../../shared/daedalus/nodeNegotiationEngine';
import { InvariantViolation } from '../src/invariants/invariants';

const fp: DeviceFingerprint = {
  model: 'TestDevice',
  os: 'android',
  osVersion: '15',
  deviceId: 'dev-test',
};

function mkProposal(): NodeJoinProposal {
  return {
    nodeId: 'n-test',
    kind: NodeKind.MOBILE,
    capabilities: MOBILE_CAPABILITIES,
    fingerprint: fp,
    operatorId: 'op1',
    initialRiskSignals: [],
    proposedAt: Date.now(),
  };
}

function mkDecision(decision: JoinDecisionKind): NodeJoinDecision {
  return { nodeId: 'n-test', decision, reason: 'test', decidedAt: Date.now() };
}

function mockTransport(decisionKind: JoinDecisionKind): NodeTransport {
  return {
    sendJoinProposal: jest.fn().mockResolvedValue(mkDecision(decisionKind)),
    sendHeartbeat: jest.fn().mockResolvedValue(undefined),
    sendPhysiology: jest.fn().mockResolvedValue(undefined),
  };
}

describe('createJoinNegotiator', () => {
  test('APPROVED sets status to ACTIVE', async () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    const decision = await neg.proposeJoin(mkProposal());
    expect(decision.decision).toBe(JoinDecisionKind.APPROVED);
    expect(neg.getStatus()).toBe(NodeStatus.ACTIVE);
  });

  test('REJECTED sets status to DETACHED', async () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.REJECTED),
      lifecycle,
    });

    await neg.proposeJoin(mkProposal());
    expect(neg.getStatus()).toBe(NodeStatus.DETACHED);
  });

  test('NEEDS_OPERATOR_APPROVAL keeps PENDING', async () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL),
      lifecycle,
    });

    await neg.proposeJoin(mkProposal());
    expect(neg.getStatus()).toBe(NodeStatus.PENDING);
  });

  test('handleDecision transitions status', () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    neg.handleDecision(mkDecision(JoinDecisionKind.APPROVED));
    expect(neg.getStatus()).toBe(NodeStatus.ACTIVE);
  });

  test('getLastDecision returns most recent', async () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    expect(neg.getLastDecision()).toBeNull();
    await neg.proposeJoin(mkProposal());
    expect(neg.getLastDecision()!.decision).toBe(JoinDecisionKind.APPROVED);
  });

  test('setBinding and getBinding', () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    expect(neg.getBinding()).toBeNull();
    const binding = createContinuityBinding('op1', 'n-test', 'default');
    neg.setBinding(binding);
    expect(neg.getBinding()).toBe(binding);
  });

  test('needsReproposal true for unknown fingerprint', () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    neg.setBinding(createContinuityBinding('op1', 'n-test', 'default'));
    expect(neg.needsReproposal(fp, [])).toBe(true);
  });

  test('needsReproposal false for known fingerprint', () => {
    const lifecycle = new NodeLifecycle();
    const neg = createJoinNegotiator({
      transport: mockTransport(JoinDecisionKind.APPROVED),
      lifecycle,
    });

    neg.setBinding(createContinuityBinding('op1', 'n-test', 'default'));
    expect(neg.needsReproposal(fp, [fp])).toBe(false);
  });
});
