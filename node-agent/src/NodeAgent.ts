import type { NodeAgentConfig } from "./NodeAgent.config";
import type { NodeAgentTransport } from "./NodeAgent.transport";
import { createLifecycleManager, LifecycleManager, LifecycleState } from "./NodeAgent.lifecycle";
import { createCapabilityManager, CapabilityManager } from "./NodeAgent.capabilities";
import { createExpressiveManager, ExpressiveManager, AgentExpressiveState } from "./NodeAgent.expressive";

export class NodeAgent {
  readonly config: NodeAgentConfig;
  private transport: NodeAgentTransport;
  readonly lifecycle: LifecycleManager;
  readonly capabilities: CapabilityManager;
  readonly expressive: ExpressiveManager;

  constructor(config: NodeAgentConfig, transport: NodeAgentTransport) {
    this.config = config;
    this.transport = transport;
    this.lifecycle = createLifecycleManager(config, transport);
    this.capabilities = createCapabilityManager(config.nodeId, transport, config.capabilities);
    this.expressive = createExpressiveManager(config.nodeId, transport);
  }

  async start(): Promise<void> {
    const joined = await this.lifecycle.join();
    if (!joined) return;

    this.lifecycle.startHeartbeat();
    this.expressive.startPeriodicSync(this.config.expressiveSyncIntervalMs);
    await this.syncCapabilities();
    await this.syncExpressive();
  }

  stop(): void {
    this.lifecycle.stopHeartbeat();
    this.expressive.stopPeriodicSync();
    this.lifecycle.setPhase("idle");
  }

  async sendHeartbeat(): Promise<void> {
    await this.lifecycle.sendHeartbeat();
  }

  async syncCapabilities(): Promise<void> {
    await this.capabilities.sync();
  }

  async syncProfile(): Promise<void> {
    await this.transport.post("/daedalus/mirror/profile", {
      nodeId: this.config.nodeId,
      profile: {
        id: this.config.nodeId,
        name: this.config.nodeName,
        kind: this.config.kind,
        model: this.config.model,
        os: this.config.os,
        osVersion: this.config.osVersion,
        operatorId: this.config.operatorId,
      },
      timestamp: new Date().toISOString(),
    });
  }

  async syncExpressive(): Promise<void> {
    await this.expressive.sync();
  }

  getPhase() {
    return this.lifecycle.getState().phase;
  }
}
