import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorStateStore } from '../../core/state/OrchestratorState.js';
import type {
  OrchestratorEventBus,
  RiskTier,
  RiskSnapshot,
} from '../../shared/types.js';
import type { PostureSnapshot } from '../posture/PostureEngine.js';

export interface RiskEngineDeps {
  logger: Logger;
  stateStore: OrchestratorStateStore;
  eventBus: OrchestratorEventBus;
}

export interface RiskAssessmentInput {
  posture: PostureSnapshot;
  nodeCount: number;
  recentEventCount: number;
}

export class RiskEngine {
  private readonly logger: Logger;

  private tier: RiskTier = 'low';
  private assessedAt: string = new Date().toISOString();
  private factors: string[] = [];

  constructor(deps: RiskEngineDeps) {
    this.logger = deps.logger;
  }

  /**
   * Evaluate risk from current posture, node count, and event volume.
   * Called by the pipeline after posture has been evaluated.
   */
  public assess(input: RiskAssessmentInput): void {
    const factors: string[] = [];
    let tier: RiskTier = 'low';

    if (input.posture.mode === 'defensive') {
      factors.push('posture:defensive');
      tier = 'elevated';
    } else if (input.posture.mode === 'elevated') {
      factors.push('posture:elevated');
      tier = 'medium';
    }

    if (input.nodeCount === 0) {
      factors.push('no_nodes_registered');
      if (tier === 'low') tier = 'medium';
    }

    if (input.recentEventCount > 100) {
      factors.push('high_event_volume');
      if (tier === 'low') tier = 'medium';
    }

    if (this.tier !== tier) {
      this.logger.info('[risk] tier changed', {
        from: this.tier,
        to: tier,
        factors,
      });
    }

    this.tier = tier;
    this.factors = factors;
    this.assessedAt = new Date().toISOString();
  }

  public getSnapshot(): RiskSnapshot {
    return {
      tier: this.tier,
      assessedAt: this.assessedAt,
      factors: [...this.factors],
    };
  }
}

export function createRiskEngine(deps: RiskEngineDeps): RiskEngine {
  return new RiskEngine(deps);
}
