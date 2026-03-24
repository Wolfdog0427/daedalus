import express from "express";
import { ApiRequest, ApiResponse, CONTRACT_VERSION, DaedalusState } from "daedalus-contract";
import { StateManager } from "../kernel/state/stateManager";
import { PostureEngine } from "../kernel/posture/postureEngine";
import { ExpressionEngine } from "../kernel/expression/expressionEngine";
import { ComfortEngine } from "../kernel/comfort/comfortEngine";
import { GovernanceEngine } from "../kernel/governance/governanceEngine";
import { defaultGovernanceConfig } from "../config/coreConfig";

export function createServer(initialState: DaedalusState) {
    const app = express();
    app.use(express.json());

    const stateManager = new StateManager(initialState);
    const postureEngine = new PostureEngine(stateManager);
    const expressionEngine = new ExpressionEngine(stateManager);
    const comfortEngine = new ComfortEngine(stateManager);
    const governanceEngine = new GovernanceEngine(stateManager, defaultGovernanceConfig);

    app.get("/state", (_req, res) => {
        res.json({
            success: true,
            state: stateManager.getState(),
            contractVersion: CONTRACT_VERSION,
        });
    });

    app.post("/posture", (req, res) => {
        const body = req.body as ApiRequest<{ posture: string }>;
        const updated = postureEngine.setPosture(body.payload.posture);
        const response: ApiResponse<DaedalusState> = {
            success: true,
            data: updated,
        };
        res.json(response);
    });

    app.post("/expression", (req, res) => {
        const body = req.body as ApiRequest<{ expression: string }>;
        const updated = expressionEngine.setExpression(body.payload.expression);
        const response: ApiResponse<DaedalusState> = {
            success: true,
            data: updated,
        };
        res.json(response);
    });

    app.post("/comfort", (req, res) => {
        const body = req.body as ApiRequest<{ comfortLevel: number }>;
        const updated = comfortEngine.setComfortLevel(body.payload.comfortLevel);
        const response: ApiResponse<DaedalusState> = {
            success: true,
            data: updated,
        };
        res.json(response);
    });

    app.post("/tier", (req, res) => {
        const body = req.body as ApiRequest<{ tier: string }>;
        const updated = governanceEngine.applyTier(body.payload.tier);
        const response: ApiResponse<DaedalusState> = {
            success: true,
            data: updated,
        };
        res.json(response);
    });

    return app;
}
