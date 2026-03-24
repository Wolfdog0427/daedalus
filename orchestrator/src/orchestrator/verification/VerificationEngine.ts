import type { Logger } from '../../infrastructure/logging.js';
import type {
  OrchestratorEventBus,
  RiskTier,
  VerificationRequirement,
  VerificationEvent,
  VerificationSnapshot,
} from '../../shared/types.js';

export interface VerificationEngineDeps {
  logger: Logger;
  eventBus: OrchestratorEventBus;
}

const TIER_TO_REQUIREMENT: Record<RiskTier, VerificationRequirement> = {
  low: 'none',
  medium: 'soft',
  elevated: 'strong',
  critical: 'strong',
};

export class VerificationEngine {
  private readonly logger: Logger;

  private requirement: VerificationRequirement = 'none';
  private lastEvent: VerificationEvent | null = null;

  constructor(deps: VerificationEngineDeps) {
    this.logger = deps.logger;
  }

  public updateFromRiskTier(tier: RiskTier): void {
    const req = TIER_TO_REQUIREMENT[tier];
    if (this.requirement !== req) {
      this.logger.info('[verification] requirement changed', {
        from: this.requirement,
        to: req,
        riskTier: tier,
      });
      this.requirement = req;
    }
  }

  public recordVerification(method: string, actor: string): void {
    this.lastEvent = {
      timestamp: new Date().toISOString(),
      method,
      actor,
    };
    this.logger.info('[verification] recorded', this.lastEvent);
  }

  public onEvent(event: any): void {
    if (event.type === 'verification.completed') {
      this.recordVerification(
        event.payload?.method ?? 'unknown',
        event.payload?.actor ?? 'unknown',
      );
    }
  }

  public getSnapshot(): VerificationSnapshot {
    return {
      requirement: this.requirement,
      lastEvent: this.lastEvent,
    };
  }
}

export function createVerificationEngine(
  deps: VerificationEngineDeps,
): VerificationEngine {
  return new VerificationEngine(deps);
}
