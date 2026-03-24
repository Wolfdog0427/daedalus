export {
  NodeId,
  NodeKind,
  NodeCapabilities,
  NodeRiskTier,
  NodeStatus,
  BatteryBand,
  ConnectivityBand,
  NodeHealthSnapshot,
  NodePosture,
  GlowProfile,
  ComfortFlag,
  NodePhysiologyState,
  DeviceFingerprint,
  NodeJoinProposal,
  JoinDecisionKind,
  NodeJoinDecision,
  NodeContinuityBinding,
  NodeSummary,
  NodeDetail,
  MOBILE_CAPABILITIES,
  NODE_HEALTH_IDLE,
  NODE_PHYSIOLOGY_IDLE,
} from '../../shared/daedalus/nodeContracts';

export type { HeartbeatSignals, HeartbeatConfig } from '../../shared/daedalus/nodeHeartbeatEngine';
export type { PhysiologySignals } from '../../shared/daedalus/nodePhysiologyEngine';

import type {
  NodeId,
  NodeKind,
  NodeCapabilities,
  DeviceFingerprint,
  NodeHealthSnapshot,
  NodePhysiologyState,
  NodeJoinProposal,
  NodeJoinDecision,
  NodeStatus,
  NodeRiskTier,
} from '../../shared/daedalus/nodeContracts';
import type { NodeTransport } from './transport';
import type { DeviceAdapter, LocalDeviceContext } from './deviceAdapter';

export interface NodeTemplateConfig {
  readonly nodeId: NodeId;
  readonly kind: NodeKind;
  readonly capabilities: NodeCapabilities;
  readonly operatorId: string;
  readonly trustDomain: string;
  readonly baseCadenceMs: number;
  readonly degradedCadenceMs: number;
}

export interface ContinuitySignals {
  readonly riskTier: NodeRiskTier;
  readonly operatorAttention: number;
  readonly emotionalTrajectory: 'stable' | 'rising' | 'falling' | 'volatile';
}

export interface NodeRuntime {
  start(): Promise<void>;
  stop(): void;
  getStatus(): NodeStatus;
  getHealth(): NodeHealthSnapshot;
  getPhysiology(): NodePhysiologyState;
  onStatusChange(handler: (status: NodeStatus) => void): () => void;
  onHealthChange(handler: (snapshot: NodeHealthSnapshot) => void): () => void;
  onPhysiologyChange(handler: (state: NodePhysiologyState) => void): () => void;
  updateContinuitySignals(signals: ContinuitySignals): void;
}
