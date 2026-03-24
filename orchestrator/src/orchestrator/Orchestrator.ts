import type {
  OrchestratorConstructorArgs,
  OrchestratorCommand,
  OrchestratorEvent,
  OrchestratorPublicAPI,
} from './types.js';
import type {
  NodeRegistrySnapshot,
  RiskSnapshot,
  VerificationSnapshot,
  ContinuityTimelineSnapshot,
} from '../shared/types.js';
import type { CapabilityDefinition } from './capabilities/CapabilityRegistry.js';
import type { NodeCapabilityState } from './capabilities/NodeCapabilityMap.js';
import type { CapabilityProfile } from './profiles/CapabilityProfileRegistry.js';
import type { GlowSnapshot } from './expressive/ExpressiveEngine.js';
import type { DaedalusNotification } from './notifications/NotificationEngine.js';

export class Orchestrator implements OrchestratorPublicAPI {
  private readonly logger;
  private readonly eventBus;
  private readonly stateStore;
  private readonly pipeline;
  private readonly presenceEngine;
  private readonly continuityEngine;
  private readonly postureEngine;
  private readonly riskEngine;
  private readonly verificationEngine;
  private readonly expressiveEngine;
  private readonly notificationEngine;
  private readonly capabilityRegistry;
  private readonly nodeCapabilityMap;
  private readonly profileRegistry;
  private readonly systemContext;
  private readonly operatorContext;

  constructor(args: OrchestratorConstructorArgs) {
    this.logger = args.logger;
    this.eventBus = args.eventBus;
    this.stateStore = args.stateStore;
    this.pipeline = args.pipeline;
    this.presenceEngine = args.presenceEngine;
    this.continuityEngine = args.continuityEngine;
    this.postureEngine = args.postureEngine;
    this.riskEngine = args.riskEngine;
    this.verificationEngine = args.verificationEngine;
    this.expressiveEngine = args.expressiveEngine;
    this.notificationEngine = args.notificationEngine;
    this.capabilityRegistry = args.capabilityRegistry;
    this.nodeCapabilityMap = args.nodeCapabilityMap;
    this.profileRegistry = args.profileRegistry;
    this.systemContext = args.systemContext;
    this.operatorContext = args.operatorContext;

    this.logger.info('[orchestrator] v0.4 initialized');
  }

  public dispatchCommand(command: OrchestratorCommand): void {
    this.logger.info('[orchestrator] dispatch command', { type: command.type });
    this.pipeline.dispatchCommand(command);
  }

  public emitEvent(event: OrchestratorEvent): void {
    this.logger.info('[orchestrator] emit event', { type: event.type });
    this.pipeline.handleInboundEvent(event);
  }

  public getStateSnapshot() {
    return this.stateStore.getSnapshot();
  }

  public getPresenceSnapshot() {
    return this.presenceEngine.getSnapshot();
  }

  public getContinuitySnapshot() {
    return this.continuityEngine.getSnapshot();
  }

  public getPostureSnapshot() {
    return this.postureEngine.getSnapshot();
  }

  public getNodesSnapshot(): NodeRegistrySnapshot {
    return this.presenceEngine.getNodeRegistrySnapshot();
  }

  public getRiskSnapshot(): RiskSnapshot {
    return this.riskEngine.getSnapshot();
  }

  public getVerificationSnapshot(): VerificationSnapshot {
    return this.verificationEngine.getSnapshot();
  }

  public getTimelineSnapshot(): ContinuityTimelineSnapshot {
    return this.continuityEngine.getTimelineSnapshot();
  }

  public getCapabilities(): CapabilityDefinition[] {
    return this.capabilityRegistry.list();
  }

  public isCapabilityEnabled(name: string): boolean {
    return this.capabilityRegistry.isEnabled(name);
  }

  public setCapabilityEnabled(name: string, enabled: boolean): CapabilityDefinition | undefined {
    return this.capabilityRegistry.setEnabled(name, enabled);
  }

  public getProfiles(): CapabilityProfile[] {
    return this.profileRegistry.list();
  }

  public applyProfile(name: string): CapabilityProfile | undefined {
    const profile = this.profileRegistry.get(name);
    if (!profile) return undefined;

    for (const [capName, enabled] of Object.entries(profile.capabilities)) {
      this.capabilityRegistry.setEnabled(capName, enabled);
    }

    this.logger.info('[profiles] applied', { name });
    return profile;
  }

  public getNodeCapabilities(nodeId: string): NodeCapabilityState | undefined {
    return this.nodeCapabilityMap.get(nodeId);
  }

  public listNodeCapabilities(): NodeCapabilityState[] {
    return this.nodeCapabilityMap.list();
  }

  public setNodeCapabilities(nodeId: string, capabilities: Record<string, boolean>): NodeCapabilityState {
    return this.nodeCapabilityMap.set(nodeId, capabilities);
  }

  public applyProfileToNode(nodeId: string, profileName: string): NodeCapabilityState | undefined {
    const profile = this.profileRegistry.get(profileName);
    if (!profile) return undefined;

    const state = this.nodeCapabilityMap.applyProfile(nodeId, profile.capabilities);
    this.logger.info('[profiles] applied to node', { nodeId, profileName });
    return state;
  }

  public negotiateCapabilitiesFromNodes(): Record<string, boolean> {
    const nodeStates = this.nodeCapabilityMap.list();
    const result: Record<string, boolean> = {};

    for (const node of nodeStates) {
      for (const [cap, enabled] of Object.entries(node.capabilities)) {
        if (!(cap in result)) {
          result[cap] = enabled;
        } else if (!enabled) {
          result[cap] = false;
        }
      }
    }

    for (const [cap, enabled] of Object.entries(result)) {
      this.capabilityRegistry.setEnabled(cap, enabled);
    }

    this.logger.info('[capabilities] negotiated from nodes', { result });
    return result;
  }

  public getGlowSnapshot(): GlowSnapshot {
    return this.expressiveEngine.getSnapshot();
  }

  public getNotifications(): DaedalusNotification[] {
    return this.notificationEngine.list();
  }

  public getSystemContext() {
    return this.systemContext.getSnapshot();
  }

  public getOperatorContext() {
    return this.operatorContext.getSnapshot();
  }
}
