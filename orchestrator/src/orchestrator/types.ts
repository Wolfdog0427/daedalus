import type { Logger } from '../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../core/state/OrchestratorState.js';
import type { PresenceEngine } from './presence/PresenceEngine.js';
import type { ContinuityEngine } from './continuity/ContinuityEngine.js';
import type { PostureEngine } from './posture/PostureEngine.js';
import type { RiskEngine } from './risk/RiskEngine.js';
import type { VerificationEngine } from './verification/VerificationEngine.js';
import type { ExpressiveEngine } from './expressive/ExpressiveEngine.js';
import type { NotificationEngine } from './notifications/NotificationEngine.js';
import type { CapabilityRegistry } from './capabilities/CapabilityRegistry.js';
import type { NodeCapabilityMap, NodeCapabilityState } from './capabilities/NodeCapabilityMap.js';
import type { CapabilityProfileRegistry, CapabilityProfile } from './profiles/CapabilityProfileRegistry.js';
import type { SystemContext } from '../core/context/SystemContext.js';
import type { OperatorContext } from '../core/context/OperatorContext.js';
import type {
  OrchestratorEventBus,
  OrchestratorPipeline,
  NodeRegistrySnapshot,
  RiskSnapshot,
  VerificationSnapshot,
  ContinuityTimelineSnapshot,
} from '../shared/types.js';
import type { CapabilityDefinition } from './capabilities/CapabilityRegistry.js';
import type { GlowSnapshot } from './expressive/ExpressiveEngine.js';
import type { DaedalusNotification } from './notifications/NotificationEngine.js';

export interface OrchestratorConstructorArgs {
  logger: Logger;
  eventBus: OrchestratorEventBus;
  stateStore: OrchestratorStateStore;
  pipeline: OrchestratorPipeline;
  presenceEngine: PresenceEngine;
  continuityEngine: ContinuityEngine;
  postureEngine: PostureEngine;
  riskEngine: RiskEngine;
  verificationEngine: VerificationEngine;
  expressiveEngine: ExpressiveEngine;
  notificationEngine: NotificationEngine;
  capabilityRegistry: CapabilityRegistry;
  nodeCapabilityMap: NodeCapabilityMap;
  profileRegistry: CapabilityProfileRegistry;
  systemContext: SystemContext;
  operatorContext: OperatorContext;
}

export interface OrchestratorCommand {
  type: string;
  payload?: any;
}

export interface OrchestratorEvent {
  type: string;
  payload?: any;
  meta?: Record<string, any>;
}

export interface OrchestratorPublicAPI {
  dispatchCommand(command: OrchestratorCommand): void;
  emitEvent(event: OrchestratorEvent): void;

  getStateSnapshot(): any;
  getPresenceSnapshot(): any;
  getContinuitySnapshot(): any;
  getPostureSnapshot(): any;
  getNodesSnapshot(): NodeRegistrySnapshot;
  getRiskSnapshot(): RiskSnapshot;
  getVerificationSnapshot(): VerificationSnapshot;
  getTimelineSnapshot(): ContinuityTimelineSnapshot;
  getCapabilities(): CapabilityDefinition[];
  isCapabilityEnabled(name: string): boolean;
  setCapabilityEnabled(name: string, enabled: boolean): CapabilityDefinition | undefined;
  getProfiles(): CapabilityProfile[];
  applyProfile(name: string): CapabilityProfile | undefined;
  getNodeCapabilities(nodeId: string): NodeCapabilityState | undefined;
  listNodeCapabilities(): NodeCapabilityState[];
  setNodeCapabilities(nodeId: string, capabilities: Record<string, boolean>): NodeCapabilityState;
  applyProfileToNode(nodeId: string, profileName: string): NodeCapabilityState | undefined;
  negotiateCapabilitiesFromNodes(): Record<string, boolean>;
  getGlowSnapshot(): GlowSnapshot;
  getNotifications(): DaedalusNotification[];

  getSystemContext(): any;
  getOperatorContext(): any;
}
