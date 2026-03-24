import {
    Capability,
    CapabilityRegistry as CapabilityRegistryType,
} from "daedalus-contract";

export class CapabilityRegistryImpl {
    private registry: CapabilityRegistryType;

    constructor(initial: CapabilityRegistryType) {
        this.registry = initial;
    }

    list(): Capability[] {
        return this.registry.capabilities;
    }
}
