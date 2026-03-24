import express, { Request, Response } from "express";
import { getNodeMirrorRegistry, CockpitNodeView } from "../mirror";
import { governanceService } from "../governance/GovernanceService";

export function createCockpitRouter() {
  const router = express.Router();

  router.get(
    "/cockpit/nodes",
    (_req: Request, res: Response<CockpitNodeView[]>) => {
      const registry = getNodeMirrorRegistry();
      res.json(registry.toCockpitView());
    },
  );

  router.get(
    "/cockpit/nodes/:id",
    (req: Request, res: Response<CockpitNodeView | { error: string }>) => {
      const registry = getNodeMirrorRegistry();
      const views = registry.toCockpitView();
      const node = views.find(v => v.id === req.params.id);

      if (!node) {
        res.status(404).json({ error: `Node "${req.params.id}" not found.` });
        return;
      }

      res.json(node);
    },
  );

  router.get(
    "/cockpit/summary",
    (_req: Request, res: Response) => {
      const registry = getNodeMirrorRegistry();
      const views = registry.toCockpitView();

      const byStatus: Record<string, number> = {};
      const byPosture: Record<string, number> = {};
      const byRisk: Record<string, number> = {};

      for (const v of views) {
        byStatus[v.status] = (byStatus[v.status] ?? 0) + 1;
        byPosture[v.posture] = (byPosture[v.posture] ?? 0) + 1;
        byRisk[v.risk] = (byRisk[v.risk] ?? 0) + 1;
      }

      const totalErrors = views.reduce((sum, v) => sum + v.errorCount, 0);
      const quarantinedCount = byStatus["quarantined"] ?? 0;
      const offlineCount = byStatus["offline"] ?? 0;
      const posture = governanceService.getPostureSnapshot();
      const drifts = governanceService.listDrifts();
      const overrides = governanceService.listOverrides();

      const actions: string[] = [];
      if (quarantinedCount > 0) actions.push(`${quarantinedCount} node(s) quarantined — review and detach or heal`);
      if (offlineCount > 0) actions.push(`${offlineCount} node(s) offline — check connectivity`);
      if (totalErrors > 10) actions.push(`High error count (${totalErrors}) — investigate failing nodes`);
      if (drifts.some(d => d.severity === "HIGH")) actions.push("HIGH-severity continuity drift active — consider override or investigation");
      if (posture.posture === "LOCKDOWN") actions.push("System in LOCKDOWN — review overrides before normal operation can resume");
      if (posture.posture === "GUARDED") actions.push("System GUARDED — monitor closely and clear drifts/overrides when resolved");

      type UrgencyLevel = "calm" | "attentive" | "elevated" | "critical";
      let urgency: UrgencyLevel = "calm";
      if (posture.posture === "ATTENTIVE" || totalErrors > 5 || offlineCount > 0) urgency = "attentive";
      if (posture.posture === "GUARDED" || quarantinedCount > 0 || totalErrors > 20) urgency = "elevated";
      if (posture.posture === "LOCKDOWN" || quarantinedCount > views.length * 0.5) urgency = "critical";

      res.json({
        totalNodes: views.length,
        byStatus,
        byPosture,
        byRisk,
        totalErrors,
        posture: posture.posture,
        postureReason: posture.reason,
        urgency,
        recommendedActions: actions,
        activeDriftCount: drifts.length,
        activeOverrideCount: overrides.length,
      });
    },
  );

  return router;
}
