import type { Logger } from '../../infrastructure/logging.js';

export interface NodeCapabilityState {
  nodeId: string;
  capabilities: Record<string, boolean>;
}

export interface NodeCapabilityMapDeps {
  logger: Logger;
}

export class NodeCapabilityMap {
  private readonly logger: Logger;
  private nodes: Map<string, NodeCapabilityState> = new Map();

  constructor(deps: NodeCapabilityMapDeps) {
    this.logger = deps.logger;
  }

  public set(nodeId: string, capabilities: Record<string, boolean>): NodeCapabilityState {
    const state: NodeCapabilityState = { nodeId, capabilities };
    this.nodes.set(nodeId, state);
    this.logger.info('[node-capabilities] set', { nodeId });
    return state;
  }

  public get(nodeId: string): NodeCapabilityState | undefined {
    return this.nodes.get(nodeId);
  }

  public list(): NodeCapabilityState[] {
    return Array.from(this.nodes.values());
  }

  public applyProfile(
    nodeId: string,
    profileCapabilities: Record<string, boolean>,
  ): NodeCapabilityState {
    const existing = this.nodes.get(nodeId)?.capabilities ?? {};
    const merged = { ...existing, ...profileCapabilities };
    const state: NodeCapabilityState = { nodeId, capabilities: merged };
    this.nodes.set(nodeId, state);
    this.logger.info('[node-capabilities] profile applied', { nodeId });
    return state;
  }
}

export function createNodeCapabilityMap(deps: NodeCapabilityMapDeps): NodeCapabilityMap {
  return new NodeCapabilityMap(deps);
}
