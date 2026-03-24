import { NodeId, NodeRiskTier, NodeStatus, NodeJoinProposal } from './nodeContracts';
import { NodeNotification, NodeNotificationType } from './nodeNotifications';

let notificationCounter = 0;

function makeId(): string {
  return `node-notif-${++notificationCounter}-${Date.now()}`;
}

export function createJoinRequestNotification(
  proposal: NodeJoinProposal,
): NodeNotification {
  return Object.freeze({
    id: makeId(),
    type: 'NODE_JOIN_REQUEST' as NodeNotificationType,
    nodeId: proposal.nodeId,
    nodeDescription: `${proposal.kind} node (${proposal.fingerprint.model}, ${proposal.fingerprint.os} ${proposal.fingerprint.osVersion})`,
    riskSummary:
      proposal.initialRiskSignals.length > 0
        ? proposal.initialRiskSignals.join(', ')
        : 'No risk signals',
    recommendedAction: 'Review and approve or reject this node',
    timestamp: Date.now(),
  });
}

export function createRiskEscalationNotification(
  nodeId: NodeId,
  previousTier: NodeRiskTier,
  newTier: NodeRiskTier,
  description: string,
): NodeNotification {
  return Object.freeze({
    id: makeId(),
    type: 'NODE_RISK_ESCALATION' as NodeNotificationType,
    nodeId,
    nodeDescription: description,
    riskSummary: `Risk tier escalated from ${previousTier} to ${newTier}`,
    recommendedAction:
      newTier === NodeRiskTier.HIGH
        ? 'Review node activity and consider quarantine'
        : 'Monitor node behavior',
    timestamp: Date.now(),
  });
}

export function createDegradedNotification(
  nodeId: NodeId,
  description: string,
  anomalySummary: string | null,
): NodeNotification {
  return Object.freeze({
    id: makeId(),
    type: 'NODE_DEGRADED' as NodeNotificationType,
    nodeId,
    nodeDescription: description,
    riskSummary: anomalySummary ?? 'Heartbeat entered degraded band',
    recommendedAction: 'Check node connectivity and battery status',
    timestamp: Date.now(),
  });
}

export function createQuarantineNotification(
  nodeId: NodeId,
  description: string,
  reason: string,
): NodeNotification {
  return Object.freeze({
    id: makeId(),
    type: 'NODE_QUARANTINE' as NodeNotificationType,
    nodeId,
    nodeDescription: description,
    riskSummary: reason,
    recommendedAction: 'Investigate quarantine cause before restoring',
    timestamp: Date.now(),
  });
}

export function createDetachNotification(
  nodeId: NodeId,
  description: string,
): NodeNotification {
  return Object.freeze({
    id: makeId(),
    type: 'NODE_DETACH_CONFIRMATION' as NodeNotificationType,
    nodeId,
    nodeDescription: description,
    riskSummary: 'Node has been detached from the fabric',
    recommendedAction: 'No action required unless node should be re-joined',
    timestamp: Date.now(),
  });
}

export function shouldNotifyOperator(
  type: NodeNotificationType,
): boolean {
  return true;
}
