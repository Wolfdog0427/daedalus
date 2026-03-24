import type { Logger } from '../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../core/state/OrchestratorState.js';
import type { PresenceEngine } from '../orchestrator/presence/PresenceEngine.js';
import type { ContinuityEngine } from '../orchestrator/continuity/ContinuityEngine.js';
import type { PostureEngine } from '../orchestrator/posture/PostureEngine.js';
import type { RiskEngine } from '../orchestrator/risk/RiskEngine.js';
import type { VerificationEngine } from '../orchestrator/verification/VerificationEngine.js';
import type { ExpressiveEngine } from '../orchestrator/expressive/ExpressiveEngine.js';
import type { NotificationEngine } from '../orchestrator/notifications/NotificationEngine.js';
import type { CapabilityRegistry } from '../orchestrator/capabilities/CapabilityRegistry.js';
import type { SystemContext } from '../core/context/SystemContext.js';
import type { OperatorContext } from '../core/context/OperatorContext.js';

// ── Event bus ──

export interface OrchestratorEventBusSubscription {
  unsubscribe(): void;
}

export interface OrchestratorEventBus {
  publish(event: any): void;
  subscribe(handler: (event: any) => void): OrchestratorEventBusSubscription;
}

// ── Pipeline ──

export interface OrchestratorPipelineDeps {
  logger: Logger;
  eventBus: OrchestratorEventBus;
  stateStore: OrchestratorStateStore;
  presenceEngine: PresenceEngine;
  continuityEngine: ContinuityEngine;
  postureEngine: PostureEngine;
  riskEngine: RiskEngine;
  verificationEngine: VerificationEngine;
  expressiveEngine: ExpressiveEngine;
  notificationEngine: NotificationEngine;
  capabilityRegistry: CapabilityRegistry;
  systemContext: SystemContext;
  operatorContext: OperatorContext;
}

export interface OrchestratorPipeline {
  handleInboundEvent(event: any): void;
  dispatchCommand(command: any): void;
}

// ── Node registry (v0.3) ──

export interface NodeDescriptor {
  id: string;
  capabilities: string[];
  lastHeartbeat: string;
  registeredAt: string;
  meta?: Record<string, any>;
}

export interface NodeRegistrySnapshot {
  nodes: Record<string, NodeDescriptor>;
  count: number;
}

// ── Risk & verification (v0.3) ──

export type RiskTier = 'low' | 'medium' | 'elevated' | 'critical';
export type VerificationRequirement = 'none' | 'soft' | 'strong';

export interface VerificationEvent {
  timestamp: string;
  method: string;
  actor: string;
}

export interface RiskSnapshot {
  tier: RiskTier;
  assessedAt: string;
  factors: string[];
}

export interface VerificationSnapshot {
  requirement: VerificationRequirement;
  lastEvent: VerificationEvent | null;
}

// ── Continuity timeline (v0.3) ──

export interface TimelineEntry {
  timestamp: string;
  type: string;
  threadId?: string;
  summary?: string;
  postureAtTime?: string;
}

export interface ContinuityTimelineSnapshot {
  entries: TimelineEntry[];
  threadIds: string[];
}
