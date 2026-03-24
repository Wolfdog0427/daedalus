import express, { Request, Response } from "express";
import { daedalusStore } from "./daedalusStore";
import { getDaedalusEventBus, DaedalusEventPayload } from "./DaedalusEventBus";
import { createGovernanceRouter } from "./governance/GovernanceRoutes";
import { createCockpitRouter } from "./cockpit/CockpitRoutes";
import { createMirrorRouter } from "./mirror/MirrorRoutes";
import { incidentService } from "./governance/IncidentService";
import { actionLog } from "./governance/ActionLog";
import {
  BeingPresenceDetail,
  CapabilityTrace,
  NegotiationApplyResult,
  NegotiationInput,
  NegotiationPreview,
  OrchestratorSnapshot,
} from "../../shared/daedalus/contracts";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";

export const daedalusRouter = express.Router();

daedalusRouter.use(createGovernanceRouter());
daedalusRouter.use(createCockpitRouter());
daedalusRouter.use(createMirrorRouter());

/**
 * GET /daedalus/events
 * Server-Sent Events stream for real-time node glow/risk and negotiation updates.
 */
daedalusRouter.get("/events", (req: Request, res: Response) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();

  const bus = getDaedalusEventBus();

  const send = (event: DaedalusEventPayload) => {
    res.write(`event: ${event.type}\n`);
    res.write(`data: ${JSON.stringify(event)}\n\n`);
  };

  const unsubscribe = bus.subscribe(send);

  res.write(": daedalus-events-stream-open\n\n");

  req.on("close", () => {
    unsubscribe();
    res.end();
  });
});

/**
 * GET /daedalus/snapshot
 * Returns the full orchestrator snapshot: nodes + beings.
 */
daedalusRouter.get(
  "/snapshot",
  (req: Request, res: Response<OrchestratorSnapshot>) => {
    const snapshot = daedalusStore.getSnapshot();
    res.json(snapshot);
  },
);

/**
 * GET /daedalus/constitution
 * Validates being constitution against current presences and behavioral field.
 */
daedalusRouter.get("/constitution", (_req: Request, res: Response) => {
  const beings = daedalusStore.getBeingPresences();
  const beingMap: Record<string, BeingPresenceDetail> = {};
  for (const b of beings) beingMap[b.id] = b;
  const behavioral = computeBehavioralField(beingMap);
  const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
  res.json(report);
});

/**
 * GET /daedalus/nodes
 * Returns all nodes from the canonical mirror registry.
 */
daedalusRouter.get("/nodes", (_req: Request, res: Response) => {
  const { getNodeMirrorRegistry } = require("./mirror/NodeMirror");
  res.json(getNodeMirrorRegistry().toCockpitView());
});

/**
 * GET /daedalus/capabilities/trace
 * Query params: nodeId, capabilityName
 */
daedalusRouter.get(
  "/capabilities/trace",
  (req: Request, res: Response<CapabilityTrace | { error: string }>) => {
    const { nodeId, capabilityName } = req.query as {
      nodeId?: string;
      capabilityName?: string;
    };

    if (!nodeId || !capabilityName) {
      res.status(400).json({
        error: "Missing required query params: nodeId, capabilityName",
      });
      return;
    }

    const trace = daedalusStore.getCapabilityTrace(nodeId, capabilityName);
    if (!trace) {
      res.status(404).json({
        error: `No trace available for capability "${capabilityName}" on node "${nodeId}".`,
      });
      return;
    }

    res.json(trace);
  },
);

/**
 * POST /daedalus/negotiations/preview
 * Body: NegotiationInput
 */
daedalusRouter.post(
  "/negotiations/preview",
  (req: Request, res: Response<NegotiationPreview | { error: string }>) => {
    const input = req.body as NegotiationInput;
    if (!input || !input.targetNodeId || !input.capabilityName || !input.requestedBy) {
      res.status(400).json({ error: "Invalid negotiation input payload." });
      return;
    }

    const preview = daedalusStore.previewNegotiation(input);
    if (!preview) {
      res.status(404).json({
        error: `Node "${input.targetNodeId}" not found for negotiation preview.`,
      });
      return;
    }

    res.json(preview);
  },
);

/**
 * POST /daedalus/negotiations/apply
 * Body: NegotiationInput
 */
daedalusRouter.post(
  "/negotiations/apply",
  (req: Request, res: Response<NegotiationApplyResult | { error: string }>) => {
    const input = req.body as NegotiationInput;
    if (!input || !input.targetNodeId || !input.capabilityName || !input.requestedBy) {
      res.status(400).json({ error: "Invalid negotiation input payload." });
      return;
    }

    const result = daedalusStore.applyNegotiation(input);
    if (!result) {
      res.status(404).json({
        error: `Node "${input.targetNodeId}" not found for negotiation apply.`,
      });
      return;
    }

    res.json(result);
  },
);

/**
 * GET /daedalus/beings/presence
 * Returns all being presence details.
 */
daedalusRouter.get(
  "/beings/presence",
  (_req: Request, res: Response<BeingPresenceDetail[]>) => {
    res.json(daedalusStore.getBeingPresences());
  },
);

/**
 * GET /daedalus/beings/:id/presence
 * Returns a single being's presence detail.
 */
daedalusRouter.get(
  "/beings/:id/presence",
  (req: Request, res: Response<BeingPresenceDetail | { error: string }>) => {
    const presence = daedalusStore.getBeingPresence(req.params.id);
    if (!presence) {
      res.status(404).json({ error: `Being "${req.params.id}" not found.` });
      return;
    }
    res.json(presence);
  },
);

/**
 * PUT /daedalus/beings/:id/presence
 * Body: Partial<BeingPresenceDetail> (patch)
 */
daedalusRouter.put(
  "/beings/:id/presence",
  (req: Request, res: Response<BeingPresenceDetail | { error: string }>) => {
    const updated = daedalusStore.updateBeingPresence(req.params.id, req.body);
    if (!updated) {
      res.status(404).json({ error: `Being "${req.params.id}" not found.` });
      return;
    }
    res.json(updated);
  },
);

// ── Event History ─────────────────────────────────────────────────────

daedalusRouter.get("/events/history", (req: Request, res: Response) => {
  const limit = parseInt(req.query.limit as string, 10) || 100;
  const type = req.query.type as string | undefined;
  const bus = getDaedalusEventBus();
  if (type) {
    res.json(bus.getHistoryByType(type as any, limit));
  } else {
    res.json(bus.getHistory(limit));
  }
});

// ── Incidents ─────────────────────────────────────────────────────────

daedalusRouter.get("/incidents", (_req: Request, res: Response) => {
  const status = _req.query.status as string | undefined;
  res.json(incidentService.listIncidents(status ? { status: status as any } : undefined));
});

daedalusRouter.get("/incidents/:id", (req: Request, res: Response) => {
  const incident = incidentService.getIncident(req.params.id);
  if (!incident) {
    res.status(404).json({ error: "Incident not found" });
    return;
  }
  res.json(incident);
});

daedalusRouter.post("/incidents", (req: Request, res: Response) => {
  const { title, notes, severity } = req.body;
  if (!title || !severity) {
    res.status(400).json({ error: "Missing required fields: title, severity" });
    return;
  }
  const validSeverities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
  if (!validSeverities.includes(severity)) {
    res.status(400).json({ error: "Invalid severity" });
    return;
  }
  const incident = incidentService.openIncident({ title, notes, severity });
  actionLog.record("OPEN_INCIDENT", { id: incident.id, title, severity });
  res.status(201).json(incident);
});

daedalusRouter.patch("/incidents/:id", (req: Request, res: Response) => {
  const updated = incidentService.updateIncident(req.params.id, req.body);
  if (!updated) {
    res.status(404).json({ error: "Incident not found" });
    return;
  }
  actionLog.record("UPDATE_INCIDENT", { id: updated.id, ...req.body }, false);
  res.json(updated);
});

daedalusRouter.post("/incidents/:id/resolve", (req: Request, res: Response) => {
  const resolved = incidentService.resolveIncident(req.params.id);
  if (!resolved) {
    res.status(404).json({ error: "Incident not found" });
    return;
  }
  res.json(resolved);
});

daedalusRouter.delete("/incidents/resolved", (_req: Request, res: Response) => {
  const cleared = incidentService.clearResolved();
  res.json({ cleared });
});

// ── Action Log & Undo ─────────────────────────────────────────────────

daedalusRouter.get("/actions", (req: Request, res: Response) => {
  const limit = parseInt(req.query.limit as string, 10) || 50;
  res.json(actionLog.list(limit));
});

daedalusRouter.post("/actions/:id/undo", (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    res.status(400).json({ error: "Invalid action ID" });
    return;
  }
  const result = actionLog.undo(id);
  if (!result.success) {
    res.status(400).json({ error: result.reason });
    return;
  }
  res.json({ success: true });
});
