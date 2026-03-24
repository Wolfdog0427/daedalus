import { DaedalusState } from "daedalus-contract";
import { StateManager } from "../state/stateManager";

export class ComfortEngine {
    constructor(private readonly stateManager: StateManager) {}

    setComfortLevel(comfortLevel: number): DaedalusState {
        return this.stateManager.update({ comfortLevel });
    }
}
