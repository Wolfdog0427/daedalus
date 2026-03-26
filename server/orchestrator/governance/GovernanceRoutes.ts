import { Router, Request, Response } from "express";
import { governanceService } from "./GovernanceService";
import { actionLog } from "./ActionLog";

export function createGovernanceRouter(): Router {
  const router = Router();

  router.get("/governance/posture", (_req: Request, res: Response) => {
    try {
      res.json(governanceService.getPostureSnapshot());
    } catch (err: any) {
      console.error("[governance] /posture error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to get posture" });
    }
  });

  router.get("/governance/overrides", (_req: Request, res: Response) => {
    try {
      res.json(governanceService.listOverrides());
    } catch (err: any) {
      console.error("[governance] /overrides GET error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to list overrides" });
    }
  });

  router.post("/governance/overrides", (req: Request, res: Response) => {
    try {
      const body = req.body;
      if (!body?.createdBy?.id || !body?.reason || !body?.scope || !body?.effect) {
        res.status(400).json({ error: "Missing required fields: createdBy.id, reason, scope, effect" });
        return;
      }
      const validScopes = ["NODE", "CAPABILITY", "GLOBAL"];
      const validEffects = ["ALLOW", "DENY", "ESCALATE"];
      if (!validScopes.includes(body.scope) || !validEffects.includes(body.effect)) {
        res.status(400).json({ error: "Invalid scope or effect value" });
        return;
      }
      const override = governanceService.applyOverride(req.body);
      actionLog.record("CREATE_OVERRIDE", { id: override.id, reason: override.reason, scope: override.scope, effect: override.effect });
      res.status(201).json(override);
    } catch (err: any) {
      console.error("[governance] /overrides POST error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to create override" });
    }
  });

  router.get("/governance/drifts", (_req: Request, res: Response) => {
    try {
      res.json(governanceService.listDrifts());
    } catch (err: any) {
      console.error("[governance] /drifts GET error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to list drifts" });
    }
  });

  router.post("/governance/drifts", (req: Request, res: Response) => {
    try {
      const body = req.body;
      if (!body?.severity || !body?.summary) {
        res.status(400).json({ error: "Missing required fields: severity, summary" });
        return;
      }
      const validSeverities = ["LOW", "MEDIUM", "HIGH"];
      if (!validSeverities.includes(body.severity)) {
        res.status(400).json({ error: "Invalid severity value" });
        return;
      }
      const drift = governanceService.recordDrift(req.body);
      actionLog.record("RECORD_DRIFT", { id: drift.id, severity: drift.severity, summary: drift.summary });
      res.status(201).json(drift);
    } catch (err: any) {
      console.error("[governance] /drifts POST error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to record drift" });
    }
  });

  router.delete("/governance/drifts", (_req: Request, res: Response) => {
    try {
      governanceService.clearDrifts();
      actionLog.record("CLEAR_DRIFTS", {}, false);
      res.status(204).end();
    } catch (err: any) {
      console.error("[governance] /drifts DELETE error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to clear drifts" });
    }
  });

  router.delete("/governance/overrides/:id", (req: Request, res: Response) => {
    try {
      const removed = governanceService.removeOverride(req.params.id);
      if (!removed) {
        res.status(404).json({ error: "Override not found" });
        return;
      }
      actionLog.record("REMOVE_OVERRIDE", { id: req.params.id }, false);
      res.status(204).end();
    } catch (err: any) {
      console.error("[governance] /overrides/:id DELETE error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to remove override" });
    }
  });

  router.delete("/governance/overrides", (_req: Request, res: Response) => {
    try {
      governanceService.clearOverrides();
      actionLog.record("CLEAR_OVERRIDES", {}, false);
      res.status(204).end();
    } catch (err: any) {
      console.error("[governance] /overrides DELETE error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to clear overrides" });
    }
  });

  router.get("/governance/votes", (_req: Request, res: Response) => {
    try {
      res.json(governanceService.listVotes());
    } catch (err: any) {
      console.error("[governance] /votes GET error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to list votes" });
    }
  });

  router.post("/governance/votes", (req: Request, res: Response) => {
    try {
      const body = req.body;
      if (!body?.being?.id || !body?.vote || typeof body?.weight !== "number") {
        res.status(400).json({ error: "Missing required fields: being.id, vote, weight" });
        return;
      }
      if (body.weight < 0 || body.weight > 1) {
        res.status(400).json({ error: "Vote weight must be between 0 and 1" });
        return;
      }
      const vote = governanceService.castVote(req.body);
      actionLog.record("CAST_VOTE", { beingId: vote.being.id, vote: vote.vote, weight: vote.weight }, false);
      res.status(201).json(vote);
    } catch (err: any) {
      console.error("[governance] /votes POST error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to cast vote" });
    }
  });

  router.delete("/governance/votes", (_req: Request, res: Response) => {
    try {
      governanceService.clearVotes();
      actionLog.record("CLEAR_VOTES", {}, false);
      res.status(204).end();
    } catch (err: any) {
      console.error("[governance] /votes DELETE error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to clear votes" });
    }
  });

  return router;
}
