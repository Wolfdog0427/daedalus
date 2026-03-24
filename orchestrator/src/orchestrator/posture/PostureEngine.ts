import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../../core/state/OrchestratorState.js';
import type { OrchestratorEventBus } from '../../shared/types.js';
import type { SystemContext } from '../../core/context/SystemContext.js';
import type { OperatorContext } from '../../core/context/OperatorContext.js';

export type PostureMode = 'idle' | 'normal' | 'elevated' | 'defensive';

export interface PostureEngineDeps {
  logger: Logger;
  stateStore: OrchestratorStateStore;
  eventBus: OrchestratorEventBus;
}

export interface PostureEngineContext {
  systemContext: SystemContext;
  operatorContext: OperatorContext;
}

export interface PostureSnapshot {
  mode: PostureMode;
  lastChangedAt: string | null;
  reason?: string;
}

export class PostureEngine {
  private readonly logger: Logger;
  private readonly stateStore: OrchestratorStateStore;
  private readonly eventBus: OrchestratorEventBus;

  private mode: PostureMode = 'normal';
  private lastChangedAt: string | null = null;
  private reason?: string;

  constructor(deps: PostureEngineDeps) {
    this.logger = deps.logger;
    this.stateStore = deps.stateStore;
    this.eventBus = deps.eventBus;
  }

  public onEvent(event: any, _ctx: PostureEngineContext) {
    switch (event.type) {
      case 'risk.detected':
        this.setMode('defensive', 'risk.detected');
        break;
      case 'risk.cleared':
        this.setMode('normal', 'risk.cleared');
        break;
      case 'system.idle':
        this.setMode('idle', 'system.idle');
        break;
      // Hook: add capability negotiation later
      default:
        break;
    }
  }

  private setMode(mode: PostureMode, reason: string) {
    if (this.mode === mode) return;

    this.mode = mode;
    this.reason = reason;
    this.lastChangedAt = new Date().toISOString();

    this.logger.info('[posture] mode changed', {
      mode: this.mode,
      reason: this.reason,
    });

    this.eventBus.publish({
      type: 'posture.changed',
      payload: {
        mode: this.mode,
        reason: this.reason,
        at: this.lastChangedAt,
      },
    });
  }

  public getSnapshot(): PostureSnapshot {
    return {
      mode: this.mode,
      lastChangedAt: this.lastChangedAt,
      reason: this.reason,
    };
  }
}

export function createPostureEngine(deps: PostureEngineDeps): PostureEngine {
  return new PostureEngine(deps);
}
