export interface Capability {
    id: string;
    name: string;
    description: string;
}

export interface CapabilityRegistry {
    capabilities: Capability[];
}
