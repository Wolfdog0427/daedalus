import { DaedalusState } from "daedalus-contract";
import { StateManager } from "../state/stateManager";

export class ExpressionEngine {
    constructor(private readonly stateManager: StateManager) {}

    setExpression(expression: string): DaedalusState {
        return this.stateManager.update({ expression });
    }
}
