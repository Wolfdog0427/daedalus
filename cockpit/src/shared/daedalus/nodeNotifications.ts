import { NodeId, NodeRiskTier } from './nodeContracts';

export type NodeNotificationType =
  | 'NODE_JOIN_REQUEST'
  | 'NODE_RISK_ESCALATION'
  | 'NODE_DEGRADED'
  | 'NODE_QUARANTINE'
  | 'NODE_DETACH_CONFIRMATION';

export interface NodeNotification {
  readonly id: string;
  readonly type: NodeNotificationType;
  readonly nodeId: NodeId;
  readonly nodeDescription: string;
  readonly riskSummary: string;
  readonly recommendedAction: string;
  readonly timestamp: number;
}

export const NODE_NOTIFICATION_IDLE: NodeNotification = Object.freeze({
  id: '',
  type: 'NODE_JOIN_REQUEST' as NodeNotificationType,
  nodeId: '',
  nodeDescription: '',
  riskSummary: '',
  recommendedAction: '',
  timestamp: 0,
});
