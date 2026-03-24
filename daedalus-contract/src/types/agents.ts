export interface DaedalusAgent {
    id: string;
    name: string;
    description: string;
    capabilities: string[];
}

export interface AgentRegistry {
    agents: DaedalusAgent[];
}
