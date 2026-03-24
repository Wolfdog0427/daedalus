import { DaedalusState } from "daedalus-contract";
import { createServer } from "./api/server";

const defaultState: DaedalusState = {
    version: "1.0.0",
    operatorId: "operator",
    activeTier: "baseline",
    posture: "observer",
    expression: "neutral",
    comfortLevel: 1,
    lastUpdated: Date.now(),
};

const app = createServer(defaultState);

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`Daedalus kernel running on port ${PORT}`);
});
