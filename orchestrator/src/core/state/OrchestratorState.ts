import type { Logger } from '../../infrastructure/logging.js';

export interface OrchestratorStateSnapshot {
  config: any;
  nodes: any;
  memory: any;
  events: any[];
  shards: any;
  audit: any[];
}

export class OrchestratorStateStore {
  private readonly logger: Logger;

  private state: OrchestratorStateSnapshot = {
    config: {},
    nodes: {},
    memory: {},
    events: [],
    shards: {},
    audit: [],
  };

  constructor(logger: Logger) {
    this.logger = logger;
  }

  public applyEvent(event: any) {
    this.state.events = [...this.state.events, event];
    this.state.audit = [
      ...this.state.audit,
      {
        type: event.type,
        at: new Date().toISOString(),
      },
    ];
  }

  public getSnapshot(): OrchestratorStateSnapshot {
    return this.state;
  }
}
