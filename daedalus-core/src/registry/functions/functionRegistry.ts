import {
    DaedalusFunction,
    FunctionRegistry as FunctionRegistryType,
} from "daedalus-contract";

export class FunctionRegistryImpl {
    private registry: FunctionRegistryType;

    constructor(initial: FunctionRegistryType) {
        this.registry = initial;
    }

    list(): DaedalusFunction[] {
        return this.registry.functions;
    }
}
