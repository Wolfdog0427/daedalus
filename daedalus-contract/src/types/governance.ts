export interface GovernanceEnvelope {
    tier: string;
    rules: string[];
    constraints: string[];
}

export interface GovernanceConfig {
    envelopes: GovernanceEnvelope[];
}
