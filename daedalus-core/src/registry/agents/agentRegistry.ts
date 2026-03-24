import {
    DaedalusAgent,
    AgentRegistry as AgentRegistryType,
} from "daedalus-contract";

export class AgentRegistryImpl {
    private registry: AgentRegistryType;

    constructor(initial: AgentRegistryType) {
        this.registry = initial;
    }

    list(): DaedalusAgent[] {
        return this.registry.agents;
    }
}
