import { DaedalusState } from "daedalus-contract";

export class StateManager {
    private state: DaedalusState;

    constructor(initialState: DaedalusState) {
        this.state = initialState;
    }

    getState(): DaedalusState {
        return this.state;
    }

    update(partial: Partial<DaedalusState>): DaedalusState {
        this.state = {
            ...this.state,
            ...partial,
            lastUpdated: Date.now(),
        };
        return this.state;
    }
}
