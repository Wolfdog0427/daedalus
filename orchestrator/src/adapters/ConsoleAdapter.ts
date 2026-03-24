import type { Logger } from '../infrastructure/logging.js';
import type {
  OrchestratorPublicAPI,
  OrchestratorCommand,
} from '../orchestrator/types.js';

export class ConsoleAdapter {
  private readonly logger: Logger;
  private readonly orchestrator: OrchestratorPublicAPI;

  constructor(logger: Logger, orchestrator: OrchestratorPublicAPI) {
    this.logger = logger;
    this.orchestrator = orchestrator;
  }

  public attach() {
    this.logger.info('[console-adapter] attached');
  }

  public sendCommand(command: OrchestratorCommand) {
    this.orchestrator.dispatchCommand(command);
  }
}
