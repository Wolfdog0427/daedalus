import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorConfig } from '../../infrastructure/config.js';

export interface SystemSnapshot {
  env: string;
  version: string;
  startedAt: string;
}

export class SystemContext {
  private readonly logger: Logger;
  private readonly config: OrchestratorConfig;
  private readonly startedAt: string;

  constructor(config: OrchestratorConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    this.startedAt = new Date().toISOString();
  }

  public getSnapshot(): SystemSnapshot {
    return {
      env: this.config.env,
      version: '0.4.0',
      startedAt: this.startedAt,
    };
  }
}

export function createSystemContext(
  config: OrchestratorConfig,
  logger: Logger,
): SystemContext {
  return new SystemContext(config, logger);
}
