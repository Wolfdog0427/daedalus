import { DaedalusState, GovernanceConfig, GovernanceEnvelope } from "daedalus-contract";
import { StateManager } from "../state/stateManager";

export class GovernanceEngine {
    constructor(
        private readonly stateManager: StateManager,
        private readonly config: GovernanceConfig
    ) {}

    getEnvelopeForTier(tier: string): GovernanceEnvelope | undefined {
        return this.config.envelopes.find((e) => e.tier === tier);
    }

    applyTier(tier: string): DaedalusState {
        const envelope = this.getEnvelopeForTier(tier);
        if (!envelope) return this.stateManager.getState();
        return this.stateManager.update({ activeTier: tier });
    }
}
