import express, { Request, Response } from "express";
import { daedalusStore } from "./daedalusStore";
import { getDaedalusEventBus, DaedalusEventPayload } from "./DaedalusEventBus";
import { createGovernanceRouter } from "./governance/GovernanceRoutes";
import {
  BeingPresenceDetail,
  CapabilityTrace,
  NegotiationApplyResult,
  NegotiationInput,
  NegotiationPreview,
  OrchestratorSnapshot,
} from "../../shared/daedalus/contracts";

export const daedalusRouter = express.Router();

daedalusRouter.use(createGovernanceRouter());

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
 * GET /daedalus/nodes
 * Returns all node presences.
 */
daedalusRouter.get("/nodes", (req: Request, res: Response) => {
  const nodes = daedalusStore.getNodes();
  res.json(nodes);
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
