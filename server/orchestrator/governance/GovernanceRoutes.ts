import { Router, Request, Response } from "express";
import { governanceService } from "./GovernanceService";

export function createGovernanceRouter(): Router {
  const router = Router();

  router.get("/governance/posture", (_req: Request, res: Response) => {
    res.json(governanceService.getPostureSnapshot());
  });

  router.get("/governance/overrides", (_req: Request, res: Response) => {
    res.json(governanceService.listOverrides());
  });

  router.post("/governance/overrides", (req: Request, res: Response) => {
    const override = governanceService.applyOverride(req.body);
    res.status(201).json(override);
  });

  router.get("/governance/drifts", (_req: Request, res: Response) => {
    res.json(governanceService.listDrifts());
  });

  router.post("/governance/drifts", (req: Request, res: Response) => {
    const drift = governanceService.recordDrift(req.body);
    res.status(201).json(drift);
  });

  return router;
}
