import { DaedalusState } from "daedalus-contract";
import { StateManager } from "../state/stateManager";

export class PostureEngine {
    constructor(private readonly stateManager: StateManager) {}

    setPosture(posture: string): DaedalusState {
        return this.stateManager.update({ posture });
    }
}
