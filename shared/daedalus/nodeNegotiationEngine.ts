import {
  NodeId,
  NodeStatus,
  NodeJoinProposal,
  NodeJoinDecision,
  JoinDecisionKind,
  DeviceFingerprint,
  NodeContinuityBinding,
} from './nodeContracts';

export function evaluateJoinProposal(
  proposal: NodeJoinProposal,
  knownFingerprints: readonly DeviceFingerprint[],
): NodeJoinDecision {
  const now = Date.now();

  if (proposal.initialRiskSignals.length > 2) {
    return Object.freeze({
      nodeId: proposal.nodeId,
      decision: JoinDecisionKind.NEEDS_OPERATOR_APPROVAL,
      reason: `High risk signals detected: ${proposal.initialRiskSignals.join(', ')}`,
      decidedAt: now,
    });
  }

  const knownMatch = knownFingerprints.find(
    fp =>
      fp.deviceId === proposal.fingerprint.deviceId &&
      fp.model === proposal.fingerprint.model,
  );

  if (!knownMatch) {
    return Object.freeze({
      nodeId: proposal.nodeId,
      decision: JoinDecisionKind.NEEDS_OPERATOR_APPROVAL,
      reason: 'Unknown device fingerprint requires operator verification',
      decidedAt: now,
    });
  }

  if (
    knownMatch.os !== proposal.fingerprint.os ||
    knownMatch.osVersion !== proposal.fingerprint.osVersion
  ) {
    return Object.freeze({
      nodeId: proposal.nodeId,
      decision: JoinDecisionKind.NEEDS_OPERATOR_APPROVAL,
      reason: 'Device fingerprint changed since last approval',
      decidedAt: now,
    });
  }

  if (!proposal.capabilities.canNegotiate) {
    return Object.freeze({
      nodeId: proposal.nodeId,
      decision: JoinDecisionKind.REJECTED,
      reason: 'Node lacks negotiation capability',
      decidedAt: now,
    });
  }

  return Object.freeze({
    nodeId: proposal.nodeId,
    decision: JoinDecisionKind.APPROVED,
    reason: 'Known device with matching fingerprint',
    decidedAt: now,
  });
}

export function applyJoinDecision(
  currentStatus: NodeStatus,
  decision: NodeJoinDecision,
): NodeStatus {
  switch (decision.decision) {
    case JoinDecisionKind.APPROVED:
      return NodeStatus.ACTIVE;
    case JoinDecisionKind.REJECTED:
      return NodeStatus.DETACHED;
    case JoinDecisionKind.NEEDS_OPERATOR_APPROVAL:
      return NodeStatus.PENDING;
    default:
      return currentStatus;
  }
}

export function shouldRepropose(
  currentBinding: NodeContinuityBinding | null,
  newFingerprint: DeviceFingerprint,
  knownFingerprints: readonly DeviceFingerprint[],
): boolean {
  if (!currentBinding) return true;

  const known = knownFingerprints.find(
    fp => fp.deviceId === newFingerprint.deviceId,
  );
  if (!known) return true;

  return (
    known.os !== newFingerprint.os ||
    known.osVersion !== newFingerprint.osVersion ||
    known.model !== newFingerprint.model
  );
}

export function createContinuityBinding(
  operatorId: string,
  nodeId: NodeId,
  trustDomain: string,
): NodeContinuityBinding {
  return Object.freeze({
    operatorId,
    nodeId,
    trustDomain,
    createdAt: Date.now(),
  });
}

export function canNodePerformPrivilegedAction(status: NodeStatus): boolean {
  return status === NodeStatus.ACTIVE;
}
