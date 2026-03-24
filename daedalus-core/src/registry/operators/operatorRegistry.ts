import { Operator, OperatorRegistry as OperatorRegistryType } from "daedalus-contract";

export class OperatorRegistryImpl {
    private registry: OperatorRegistryType;

    constructor(initial: OperatorRegistryType) {
        this.registry = initial;
    }

    getRegistry(): OperatorRegistryType {
        return this.registry;
    }

    getPrimaryOperator(): Operator | undefined {
        return this.registry.operators.find(
            (op) => op.id === this.registry.primaryOperatorId
        );
    }
}
