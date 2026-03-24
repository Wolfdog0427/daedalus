export type NodeId = string;

export enum NodeKind {
  MOBILE = 'MOBILE',
  DESKTOP = 'DESKTOP',
  SERVER = 'SERVER',
  EMBEDDED = 'EMBEDDED',
}

export interface NodeCapabilities {
  readonly canNotify: boolean;
  readonly canRenderCockpit: boolean;
  readonly canStoreContinuity: boolean;
  readonly canExpressPhysiology: boolean;
  readonly canNegotiate: boolean;
  readonly canHandoff: boolean;
}

export enum NodeRiskTier {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  QUARANTINED = 'QUARANTINED',
}

export enum NodeStatus {
  PENDING = 'PENDING',
  ACTIVE = 'ACTIVE',
  DEGRADED = 'DEGRADED',
  QUARANTINED = 'QUARANTINED',
  DETACHED = 'DETACHED',
}

export type BatteryBand = 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
export type ConnectivityBand = 'STRONG' | 'MODERATE' | 'WEAK' | 'OFFLINE';

export interface NodeHealthSnapshot {
  readonly nodeId: NodeId;
  readonly liveness: boolean;
  readonly batteryBand: BatteryBand;
  readonly connectivityBand: ConnectivityBand;
  readonly anomalySummary: string | null;
  readonly degraded: boolean;
  readonly timestamp: number;
}

export type NodePosture = 'CALM' | 'ALERT' | 'DEFENSIVE' | 'DEGRADED';

export interface GlowProfile {
  readonly intensity: number;
  readonly colorBand: string;
  readonly motionPattern: 'steady' | 'pulse' | 'breathe' | 'flicker';
}

export type ComfortFlag =
  | 'LOW_BATTERY'
  | 'UNSTABLE_NETWORK'
  | 'HIGH_RISK_CONTEXT'
  | 'QUARANTINE_RISK';

export interface NodePhysiologyState {
  readonly nodeId: NodeId;
  readonly posture: NodePosture;
  readonly glowProfile: GlowProfile;
  readonly attentionWeight: number;
  readonly comfortFlags: readonly ComfortFlag[];
  readonly timestamp: number;
}

export interface DeviceFingerprint {
  readonly model: string;
  readonly os: string;
  readonly osVersion: string;
  readonly deviceId: string;
}

export interface NodeJoinProposal {
  readonly nodeId: NodeId;
  readonly kind: NodeKind;
  readonly capabilities: NodeCapabilities;
  readonly fingerprint: DeviceFingerprint;
  readonly operatorId: string;
  readonly initialRiskSignals: readonly string[];
  readonly proposedAt: number;
}

export enum JoinDecisionKind {
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  NEEDS_OPERATOR_APPROVAL = 'NEEDS_OPERATOR_APPROVAL',
}

export interface NodeJoinDecision {
  readonly nodeId: NodeId;
  readonly decision: JoinDecisionKind;
  readonly reason: string;
  readonly decidedAt: number;
}

export interface NodeContinuityBinding {
  readonly operatorId: string;
  readonly nodeId: NodeId;
  readonly trustDomain: string;
  readonly createdAt: number;
}

export interface NodeSummary {
  readonly nodeId: NodeId;
  readonly kind: NodeKind;
  readonly status: NodeStatus;
  readonly riskTier: NodeRiskTier;
  readonly batteryBand: BatteryBand;
  readonly connectivityBand: ConnectivityBand;
  readonly posture: NodePosture;
  readonly lastHeartbeat: number;
}

export interface NodeDetail {
  readonly nodeId: NodeId;
  readonly kind: NodeKind;
  readonly status: NodeStatus;
  readonly riskTier: NodeRiskTier;
  readonly capabilities: NodeCapabilities;
  readonly fingerprint: DeviceFingerprint;
  readonly binding: NodeContinuityBinding | null;
  readonly health: NodeHealthSnapshot;
  readonly physiology: NodePhysiologyState;
  readonly joinHistory: readonly NodeJoinDecision[];
}

export const MOBILE_CAPABILITIES: NodeCapabilities = Object.freeze({
  canNotify: true,
  canRenderCockpit: false,
  canStoreContinuity: true,
  canExpressPhysiology: true,
  canNegotiate: true,
  canHandoff: true,
});

export const NODE_HEALTH_IDLE: NodeHealthSnapshot = Object.freeze({
  nodeId: '',
  liveness: false,
  batteryBand: 'HIGH' as BatteryBand,
  connectivityBand: 'STRONG' as ConnectivityBand,
  anomalySummary: null,
  degraded: false,
  timestamp: 0,
});

export const NODE_PHYSIOLOGY_IDLE: NodePhysiologyState = Object.freeze({
  nodeId: '',
  posture: 'CALM' as NodePosture,
  glowProfile: Object.freeze({ intensity: 0.5, colorBand: '#7a7a7a', motionPattern: 'steady' as const }),
  attentionWeight: 0.5,
  comfortFlags: Object.freeze([]) as readonly ComfortFlag[],
  timestamp: 0,
});
