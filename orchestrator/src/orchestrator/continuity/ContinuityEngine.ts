import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../../core/state/OrchestratorState.js';
import type {
  OrchestratorEventBus,
  TimelineEntry,
  ContinuityTimelineSnapshot,
} from '../../shared/types.js';
import type { SystemContext } from '../../core/context/SystemContext.js';
import type { OperatorContext } from '../../core/context/OperatorContext.js';

export interface ContinuityEngineDeps {
  logger: Logger;
  stateStore: OrchestratorStateStore;
  eventBus: OrchestratorEventBus;
}

export interface ContinuityEngineContext {
  systemContext: SystemContext;
  operatorContext: OperatorContext;
}

export interface ContinuitySnapshot {
  threads: Record<string, any>;
}

const MAX_TIMELINE_ENTRIES = 200;

export class ContinuityEngine {
  private readonly logger: Logger;
  private readonly stateStore: OrchestratorStateStore;
  private readonly eventBus: OrchestratorEventBus;

  private threads: Record<string, any> = {};
  private timeline: TimelineEntry[] = [];

  constructor(deps: ContinuityEngineDeps) {
    this.logger = deps.logger;
    this.stateStore = deps.stateStore;
    this.eventBus = deps.eventBus;
  }

  public onEvent(event: any, _ctx: ContinuityEngineContext) {
    this.recordTimelineEntry(event);

    switch (event.type) {
      case 'conversation.message':
        this.handleConversationMessage(event);
        break;
      default:
        break;
    }
  }

  private recordTimelineEntry(event: any) {
    const entry: TimelineEntry = {
      timestamp: new Date().toISOString(),
      type: event.type,
      threadId: event.payload?.threadId,
      summary: this.summarizeEvent(event),
    };

    this.timeline.push(entry);
    if (this.timeline.length > MAX_TIMELINE_ENTRIES) {
      this.timeline.shift();
    }
  }

  private summarizeEvent(event: any): string {
    switch (event.type) {
      case 'conversation.message':
        return `${event.payload?.role ?? 'unknown'}: ${(event.payload?.content ?? '').slice(0, 80)}`;
      case 'posture.changed':
        return `posture → ${event.payload?.mode}`;
      case 'node.joined':
        return `node joined: ${event.payload?.id}`;
      default:
        return event.type;
    }
  }

  private handleConversationMessage(event: any) {
    const threadId = event.payload.threadId ?? 'default';
    const existing = this.threads[threadId] ?? { messages: [] };

    const message = {
      id: event.payload.id,
      role: event.payload.role,
      content: event.payload.content,
      at: new Date().toISOString(),
    };

    this.threads[threadId] = {
      ...existing,
      messages: [...existing.messages, message],
    };
  }

  public getSnapshot(): ContinuitySnapshot {
    return {
      threads: this.threads,
    };
  }

  public getTimelineSnapshot(): ContinuityTimelineSnapshot {
    return {
      entries: [...this.timeline],
      threadIds: Object.keys(this.threads),
    };
  }
}

export function createContinuityEngine(
  deps: ContinuityEngineDeps,
): ContinuityEngine {
  return new ContinuityEngine(deps);
}
