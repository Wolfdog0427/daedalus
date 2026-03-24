import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../../core/state/OrchestratorState.js';
import type {
  OrchestratorEventBus,
  NodeDescriptor,
  NodeRegistrySnapshot,
} from '../../shared/types.js';
import type { SystemContext } from '../../core/context/SystemContext.js';
import type { OperatorContext } from '../../core/context/OperatorContext.js';

export interface PresenceEngineDeps {
  logger: Logger;
  stateStore: OrchestratorStateStore;
  eventBus: OrchestratorEventBus;
}

export interface PresenceEngineContext {
  systemContext: SystemContext;
  operatorContext: OperatorContext;
}

export interface PresenceSnapshot {
  nodes: Record<string, any>;
  beings: Record<string, any>;
  sessions: Record<string, any>;
}

export class PresenceEngine {
  private readonly logger: Logger;
  private readonly stateStore: OrchestratorStateStore;
  private readonly eventBus: OrchestratorEventBus;

  private nodeRegistry: Record<string, NodeDescriptor> = {};
  private beings: Record<string, any> = {};
  private sessions: Record<string, any> = {};

  constructor(deps: PresenceEngineDeps) {
    this.logger = deps.logger;
    this.stateStore = deps.stateStore;
    this.eventBus = deps.eventBus;
  }

  public onEvent(event: any, _ctx: PresenceEngineContext) {
    switch (event.type) {
      case 'node.joined': {
        const id = event.payload.id;
        const now = new Date().toISOString();
        this.nodeRegistry[id] = {
          id,
          capabilities: event.payload.capabilities ?? [],
          lastHeartbeat: now,
          registeredAt: this.nodeRegistry[id]?.registeredAt ?? now,
          meta: event.payload.meta,
        };
        this.logger.info('[presence] node registered', { id });
        break;
      }
      case 'node.heartbeat': {
        const id = event.payload.id;
        if (this.nodeRegistry[id]) {
          this.nodeRegistry[id].lastHeartbeat = new Date().toISOString();
          if (event.payload.capabilities) {
            this.nodeRegistry[id].capabilities = event.payload.capabilities;
          }
        }
        break;
      }
      case 'node.capabilities': {
        const id = event.payload.id;
        if (this.nodeRegistry[id]) {
          this.nodeRegistry[id].capabilities = event.payload.capabilities ?? [];
          this.logger.info('[presence] capabilities updated', { id });
        }
        break;
      }
      case 'being.registered':
        this.beings[event.payload.id] = {
          ...event.payload,
          registeredAt: new Date().toISOString(),
        };
        break;
      case 'session.started':
        this.sessions[event.payload.id] = {
          ...event.payload,
          startedAt: new Date().toISOString(),
        };
        break;
      case 'session.ended':
        delete this.sessions[event.payload.id];
        break;
      default:
        break;
    }
  }

  public getSnapshot(): PresenceSnapshot {
    return {
      nodes: this.nodeRegistry,
      beings: this.beings,
      sessions: this.sessions,
    };
  }

  public getNodeRegistrySnapshot(): NodeRegistrySnapshot {
    return {
      nodes: { ...this.nodeRegistry },
      count: Object.keys(this.nodeRegistry).length,
    };
  }
}

export function createPresenceEngine(deps: PresenceEngineDeps): PresenceEngine {
  return new PresenceEngine(deps);
}
