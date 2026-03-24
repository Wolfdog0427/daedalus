export type {
  NodeTemplateConfig,
  ContinuitySignals,
  NodeRuntime,
} from './contracts';

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
  MOBILE_CAPABILITIES,
  NODE_HEALTH_IDLE,
  NODE_PHYSIOLOGY_IDLE,
} from './contracts';

export type { NodeTransport } from './transport';
export type { DeviceAdapter, LocalDeviceContext, ThermalState } from './deviceAdapter';
export { IDLE_DEVICE_CONTEXT } from './deviceAdapter';

export { NodeLifecycle } from './lifecycle/stateMachine';
export {
  assertNoSilentJoin,
  assertOperatorSovereignty,
  assertNotQuarantined,
  assertNotDetached,
  InvariantViolation,
} from './invariants/invariants';

export { createHeartbeatEngine } from './heartbeatEngine';
export type { HeartbeatEngine, HeartbeatEngineConfig } from './heartbeatEngine';

export { createJoinNegotiator } from './joinNegotiator';
export type { JoinNegotiator, JoinNegotiatorConfig } from './joinNegotiator';

export { createPhysiologyDriver } from './physiologyDriver';
export type { PhysiologyDriver, PhysiologyDriverConfig } from './physiologyDriver';

export { createNodeRuntime } from './runtime';

export { createMobileAdapter } from './adapters/mobile';
export { createDesktopAdapter } from './adapters/desktop';
export { createServerAdapter } from './adapters/server';
