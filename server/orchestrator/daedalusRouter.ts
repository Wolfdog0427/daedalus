import express, { Request, Response } from "express";
import { daedalusStore } from "./daedalusStore";
import { getDaedalusEventBus, DaedalusEventPayload } from "./DaedalusEventBus";
import { createGovernanceRouter } from "./governance/GovernanceRoutes";
import { createCockpitRouter } from "./cockpit/CockpitRoutes";
import { createMirrorRouter } from "./mirror/MirrorRoutes";
import { incidentService } from "./governance/IncidentService";
import { actionLog } from "./governance/ActionLog";
import { strategyService } from "./strategy/StrategyService";
import { processMessage, getChatHistory, clearChatHistory, getWelcomeMessage, getChatHelp } from "./chat/ChatService";
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
  (req: Request, res: Response<OrchestratorSnapshot | { error: string }>) => {
    try {
      const snapshot = daedalusStore.getSnapshot();
      res.json(snapshot);
    } catch (err: any) {
      console.error("[daedalus] /snapshot error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to build snapshot" });
    }
  },
);

/**
 * GET /daedalus/constitution
 * Validates being constitution against current presences and behavioral field.
 */
daedalusRouter.get("/constitution", (_req: Request, res: Response) => {
  try {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    res.json(report);
  } catch (err: any) {
    console.error("[daedalus] /constitution error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to validate constitution" });
  }
});

/**
 * GET /daedalus/strategy
 * Returns the current strategy alignment evaluation plus kernel tick metadata
 * (posture, drift, self-correction state).
 * Routes through kernel tickKernel for the full pipeline.
 */
daedalusRouter.get("/strategy", (_req: Request, res: Response) => {
  try {
    const evaluation = strategyService.evaluate();
    const tick = strategyService.getLastTickResult();
    res.json({
      ...evaluation,
      posture: tick?.posture ?? null,
      drift: tick?.drift ?? null,
      selfCorrected: tick?.selfCorrected ?? false,
      trend: tick?.trend ?? null,
      escalation: tick?.escalation ?? null,
      safeMode: tick?.safeMode ?? null,
    });
  } catch (err: any) {
    console.error("[daedalus] /strategy error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to evaluate strategy" });
  }
});

/**
 * GET /daedalus/telemetry
 * Returns the kernel alignment telemetry snapshot — recent strategy
 * evaluations, alignment history, drift analysis, and telemetry events.
 */
daedalusRouter.get("/telemetry", (_req: Request, res: Response) => {
  try {
    const snapshot = strategyService.getTelemetrySnapshot();
    res.json(snapshot);
  } catch (err: any) {
    console.error("[daedalus] /telemetry error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch telemetry" });
  }
});

/**
 * GET /daedalus/alignment-config
 * Returns the current operator-controlled alignment configuration.
 */
daedalusRouter.get("/alignment-config", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getAlignmentConfig());
  } catch (err: any) {
    console.error("[daedalus] /alignment-config GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch alignment config" });
  }
});

/**
 * POST /daedalus/alignment-config
 * Updates the operator-controlled alignment configuration.
 * Runs the change through the auto-approval gate first.
 */
daedalusRouter.post("/alignment-config", (req: Request, res: Response) => {
  try {
    const proposal = {
      id: `ac-${Date.now()}`,
      kind: "alignment_config" as const,
      description: "Alignment config update via operator",
      payload: req.body ?? {},
      proposedAt: Date.now(),
      proposedBy: "operator",
    };

    const decision = strategyService.submitChangeProposal(proposal);

    const updated = strategyService.updateAlignmentConfig(req.body ?? {});
    getDaedalusEventBus().publish({
      type: "ALIGNMENT_CONFIG_CHANGED",
      timestamp: new Date().toISOString(),
      summary: "Alignment configuration updated by operator",
    });
    res.json({ ...updated, approval: decision });
  } catch (err: any) {
    console.error("[daedalus] /alignment-config POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to update alignment config" });
  }
});

/**
 * GET /daedalus/proposals/pending
 * Returns Daedalus-initiated proposals awaiting operator approval.
 */
daedalusRouter.get("/proposals/pending", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getPendingDaedalusProposals());
  } catch (err: any) {
    console.error("[daedalus] /proposals/pending GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch pending proposals" });
  }
});

/**
 * GET /daedalus/proposals/history
 * Returns resolved proposal history with effect tracking.
 */
daedalusRouter.get("/proposals/history", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getProposalHistory());
  } catch (err: any) {
    console.error("[daedalus] /proposals/history GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch proposal history" });
  }
});

/**
 * POST /daedalus/proposals/:id/approve
 * Approve a pending Daedalus proposal.
 */
daedalusRouter.post("/proposals/:id/approve", (req: Request, res: Response) => {
  try {
    const result = strategyService.approveDaedalusProposal(req.params.id);
    if (!result) {
      res.status(404).json({ error: "Proposal not found or already resolved" });
      return;
    }
    res.json(result);
  } catch (err: any) {
    console.error("[daedalus] /proposals/:id/approve error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to approve proposal" });
  }
});

/**
 * POST /daedalus/proposals/:id/deny
 * Deny a pending Daedalus proposal.
 */
daedalusRouter.post("/proposals/:id/deny", (req: Request, res: Response) => {
  try {
    const result = strategyService.denyDaedalusProposal(req.params.id);
    if (!result) {
      res.status(404).json({ error: "Proposal not found or already resolved" });
      return;
    }
    res.json(result);
  } catch (err: any) {
    console.error("[daedalus] /proposals/:id/deny error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to deny proposal" });
  }
});

/**
 * POST /daedalus/propose-change
 * Submit a change proposal for auto-approval evaluation.
 * The change is NOT applied — only evaluated.
 */
daedalusRouter.post("/propose-change", (req: Request, res: Response) => {
  try {
    const body = req.body ?? {};
    if (!body.kind || !body.description) {
      res.status(400).json({ error: "Missing required fields: kind, description" });
      return;
    }
    const proposal = {
      id: body.id ?? `cp-${Date.now()}`,
      kind: body.kind,
      description: body.description,
      payload: body.payload ?? {},
      proposedAt: Date.now(),
      proposedBy: body.proposedBy ?? "operator",
    };
    const decision = strategyService.submitChangeProposal(proposal);
    res.json(decision);
  } catch (err: any) {
    console.error("[daedalus] /propose-change error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to evaluate change proposal" });
  }
});

/**
 * GET /daedalus/approval-gate
 * Returns the current approval gate config and recent decisions.
 */
daedalusRouter.get("/approval-gate", (_req: Request, res: Response) => {
  try {
    res.json({
      config: strategyService.getApprovalGateConfig(),
      recentDecisions: strategyService.getRecentApprovals(),
    });
  } catch (err: any) {
    console.error("[daedalus] /approval-gate GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch approval gate" });
  }
});

/**
 * POST /daedalus/approval-gate/config
 * Updates the approval gate configuration.
 */
daedalusRouter.post("/approval-gate/config", (req: Request, res: Response) => {
  try {
    const updated = strategyService.updateApprovalGateConfig(req.body ?? {});
    res.json(updated);
  } catch (err: any) {
    console.error("[daedalus] /approval-gate/config POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to update approval gate config" });
  }
});

/**
 * GET /daedalus/regulation
 * Returns the current regulation config and last regulation output.
 */
daedalusRouter.get("/regulation", (_req: Request, res: Response) => {
  try {
    res.json({
      config: strategyService.getRegulationConfig(),
      lastOutput: strategyService.getLastRegulationOutput(),
    });
  } catch (err: any) {
    console.error("[daedalus] /regulation GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch regulation state" });
  }
});

/**
 * POST /daedalus/regulation/config
 * Updates the regulation loop configuration (operator tuning).
 */
daedalusRouter.post("/regulation/config", (req: Request, res: Response) => {
  try {
    const updated = strategyService.updateRegulationConfig(req.body ?? {});
    getDaedalusEventBus().publish({
      type: "ALIGNMENT_CONFIG_CHANGED",
      timestamp: new Date().toISOString(),
      summary: "Regulation config updated by operator",
    });
    res.json(updated);
  } catch (err: any) {
    console.error("[daedalus] /regulation/config POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to update regulation config" });
  }
});

/**
 * POST /daedalus/classify-change
 * Classifies a change's impact and invariant touch using the surface model.
 */
daedalusRouter.post("/classify-change", (req: Request, res: Response) => {
  try {
    const body = req.body ?? {};
    if (!body.surfaces || !body.depth) {
      res.status(400).json({ error: "Missing required fields: surfaces, depth" });
      return;
    }
    const result = strategyService.classifyChange(body);
    res.json(result);
  } catch (err: any) {
    console.error("[daedalus] /classify-change error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to classify change" });
  }
});

/**
 * GET /daedalus/rollback-registry
 * Returns the current rollback registry state: active changes, recent rollbacks.
 */
daedalusRouter.get("/rollback-registry", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getRollbackRegistrySnapshot());
  } catch (err: any) {
    console.error("[daedalus] /rollback-registry GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch rollback registry" });
  }
});

/**
 * POST /daedalus/rollback-registry/register
 * Register a change for tracked evaluation.
 */
daedalusRouter.post("/rollback-registry/register", (req: Request, res: Response) => {
  try {
    const body = req.body ?? {};
    if (!body.id || !body.description) {
      res.status(400).json({ error: "Missing required fields: id, description" });
      return;
    }
    const record = strategyService.registerTrackedChange({
      id: body.id,
      description: body.description,
      evaluationWindow: body.evaluationWindow ?? 100,
      baselineAlignment: body.baselineAlignment ?? 0,
      surfaces: body.surfaces ?? [],
      impact: body.impact ?? "low",
      rollbackPayload: body.rollbackPayload ?? {},
    });
    res.status(201).json(record);
  } catch (err: any) {
    console.error("[daedalus] /rollback-registry/register error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to register change" });
  }
});

/**
 * GET /daedalus/rollback-registry/config
 * Returns the rollback config.
 */
daedalusRouter.get("/rollback-registry/config", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getRollbackConfig());
  } catch (err: any) {
    console.error("[daedalus] /rollback-registry/config GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch rollback config" });
  }
});

/**
 * POST /daedalus/rollback-registry/config
 * Updates rollback config.
 */
daedalusRouter.post("/rollback-registry/config", (req: Request, res: Response) => {
  try {
    const updated = strategyService.updateRollbackConfig(req.body ?? {});
    res.json(updated);
  } catch (err: any) {
    console.error("[daedalus] /rollback-registry/config POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to update rollback config" });
  }
});

// ── Operator Identity Endpoints ──────────────────────────────────────

/**
 * GET /daedalus/operator/trust
 * Returns the operator trust cockpit snapshot (read-only, no config mutation).
 */
daedalusRouter.get("/operator/trust", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getOperatorTrustSnapshot());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get operator trust" });
  }
});

/**
 * POST /daedalus/operator/bind
 * Bind an operator profile. Body: OperatorProfile.
 */
daedalusRouter.post("/operator/bind", (req: Request, res: Response) => {
  try {
    const profile = req.body;
    if (!profile?.id || !profile?.displayName) {
      res.status(400).json({ error: "Missing required fields: id, displayName" });
      return;
    }
    const state = strategyService.bindOperatorProfile(profile);
    res.json(state);
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to bind operator" });
  }
});

/**
 * POST /daedalus/operator/unbind
 * Unbind the current operator.
 */
daedalusRouter.post("/operator/unbind", (_req: Request, res: Response) => {
  try {
    const state = strategyService.unbindCurrentOperator();
    res.json(state);
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to unbind operator" });
  }
});

/**
 * POST /daedalus/operator/observation
 * Submit an operator observation for trust calibration.
 */
daedalusRouter.post("/operator/observation", (req: Request, res: Response) => {
  try {
    const result = strategyService.submitOperatorObservation(req.body);
    res.json({
      trustScore: result.state.trustScore,
      allowHighRiskActions: result.allowHighRiskActions,
      suspicious: result.suspicious,
    });
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to process observation" });
  }
});

/**
 * GET /daedalus/operator/high-risk-log
 * Returns recent high-risk decision log entries.
 */
daedalusRouter.get("/operator/high-risk-log", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getRecentHighRiskLog());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get high-risk log" });
  }
});

/**
 * POST /daedalus/operator/freeze
 * Enable constitutional freeze. Body: { reason: string }
 */
daedalusRouter.post("/operator/freeze", (req: Request, res: Response) => {
  try {
    const reason = req.body?.reason ?? "operator_requested";
    res.json(strategyService.setConstitutionalFreeze(reason));
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to enable freeze" });
  }
});

/**
 * POST /daedalus/operator/unfreeze
 * Disable constitutional freeze.
 */
daedalusRouter.post("/operator/unfreeze", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.clearConstitutionalFreeze());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to disable freeze" });
  }
});

/**
 * GET /daedalus/operator/freeze
 * Get constitutional freeze state.
 */
daedalusRouter.get("/operator/freeze", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getConstitutionalFreezeState());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get freeze state" });
  }
});

/**
 * POST /daedalus/operator/attunement/start
 * Start the first-run attunement flow.
 */
daedalusRouter.post("/operator/attunement/start", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.startOperatorAttunement());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to start attunement" });
  }
});

/**
 * POST /daedalus/operator/attunement/advance
 * Advance the attunement flow to the next step.
 */
daedalusRouter.post("/operator/attunement/advance", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.advanceOperatorAttunement());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to advance attunement" });
  }
});

/**
 * GET /daedalus/operator/attunement
 * Get current attunement state.
 */
daedalusRouter.get("/operator/attunement", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getOperatorAttunementState());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get attunement" });
  }
});

/**
 * GET /daedalus/operator/introspect
 * Get introspection (why this posture?).
 */
daedalusRouter.get("/operator/introspect", (_req: Request, res: Response) => {
  try {
    res.json({ explanation: strategyService.getOperatorIntrospection() });
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to introspect" });
  }
});

/**
 * GET /daedalus/operator/timeline
 * Get the relationship timeline.
 */
daedalusRouter.get("/operator/timeline", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getOperatorTimeline());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get timeline" });
  }
});

/**
 * GET /daedalus/operator/trust-drift
 * Get trust drift samples for dashboard.
 */
daedalusRouter.get("/operator/trust-drift", (_req: Request, res: Response) => {
  try {
    res.json(strategyService.getOperatorTrustDrift());
  } catch (err: any) {
    res.status(500).json({ error: err?.message ?? "Failed to get trust drift" });
  }
});

/**
 * GET /daedalus/nodes
 * Returns all nodes from the canonical mirror registry.
 */
daedalusRouter.get("/nodes", (_req: Request, res: Response) => {
  try {
    const { getNodeMirrorRegistry } = require("./mirror/NodeMirror");
    res.json(getNodeMirrorRegistry().toCockpitView());
  } catch (err: any) {
    console.error("[daedalus] /nodes error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch nodes" });
  }
});

/**
 * GET /daedalus/capabilities/trace
 * Query params: nodeId, capabilityName
 */
daedalusRouter.get(
  "/capabilities/trace",
  (req: Request, res: Response<CapabilityTrace | { error: string }>) => {
    try {
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
    } catch (err: any) {
      console.error("[daedalus] /capabilities/trace error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to fetch capability trace" });
    }
  },
);

/**
 * POST /daedalus/negotiations/preview
 * Body: NegotiationInput
 */
daedalusRouter.post(
  "/negotiations/preview",
  (req: Request, res: Response<NegotiationPreview | { error: string }>) => {
    try {
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
    } catch (err: any) {
      console.error("[daedalus] /negotiations/preview error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to preview negotiation" });
    }
  },
);

/**
 * POST /daedalus/negotiations/apply
 * Body: NegotiationInput
 */
daedalusRouter.post(
  "/negotiations/apply",
  (req: Request, res: Response<NegotiationApplyResult | { error: string }>) => {
    try {
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
    } catch (err: any) {
      console.error("[daedalus] /negotiations/apply error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to apply negotiation" });
    }
  },
);

/**
 * GET /daedalus/beings/presence
 * Returns all being presence details.
 */
daedalusRouter.get(
  "/beings/presence",
  (_req: Request, res: Response<BeingPresenceDetail[] | { error: string }>) => {
    try {
      res.json(daedalusStore.getBeingPresences());
    } catch (err: any) {
      console.error("[daedalus] /beings/presence error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to fetch beings" });
    }
  },
);

/**
 * GET /daedalus/beings/:id/presence
 * Returns a single being's presence detail.
 */
daedalusRouter.get(
  "/beings/:id/presence",
  (req: Request, res: Response<BeingPresenceDetail | { error: string }>) => {
    try {
      const presence = daedalusStore.getBeingPresence(req.params.id);
      if (!presence) {
        res.status(404).json({ error: `Being "${req.params.id}" not found.` });
        return;
      }
      res.json(presence);
    } catch (err: any) {
      console.error("[daedalus] /beings/:id/presence error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to fetch being" });
    }
  },
);

/**
 * PUT /daedalus/beings/:id/presence
 * Body: Partial<BeingPresenceDetail> (patch)
 */
daedalusRouter.put(
  "/beings/:id/presence",
  (req: Request, res: Response<BeingPresenceDetail | { error: string }>) => {
    try {
      const updated = daedalusStore.updateBeingPresence(req.params.id, req.body);
      if (!updated) {
        res.status(404).json({ error: `Being "${req.params.id}" not found.` });
        return;
      }
      res.json(updated);
    } catch (err: any) {
      console.error("[daedalus] PUT beings/:id/presence error:", err?.message);
      res.status(500).json({ error: err?.message ?? "Failed to update being presence" });
    }
  },
);

// ── Event History ─────────────────────────────────────────────────────

daedalusRouter.get("/events/history", (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string, 10) || 100;
    const type = req.query.type as string | undefined;
    const bus = getDaedalusEventBus();
    if (type) {
      res.json(bus.getHistoryByType(type as any, limit));
    } else {
      res.json(bus.getHistory(limit));
    }
  } catch (err: any) {
    console.error("[daedalus] /events/history error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch event history" });
  }
});

// ── Incidents ─────────────────────────────────────────────────────────

daedalusRouter.get("/incidents", (_req: Request, res: Response) => {
  try {
    const status = _req.query.status as string | undefined;
    res.json(incidentService.listIncidents(status ? { status: status as any } : undefined));
  } catch (err: any) {
    console.error("[daedalus] /incidents GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to list incidents" });
  }
});

daedalusRouter.get("/incidents/:id", (req: Request, res: Response) => {
  try {
    const incident = incidentService.getIncident(req.params.id);
    if (!incident) {
      res.status(404).json({ error: "Incident not found" });
      return;
    }
    res.json(incident);
  } catch (err: any) {
    console.error("[daedalus] /incidents/:id GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to get incident" });
  }
});

daedalusRouter.post("/incidents", (req: Request, res: Response) => {
  try {
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
  } catch (err: any) {
    console.error("[daedalus] /incidents POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to open incident" });
  }
});

daedalusRouter.patch("/incidents/:id", (req: Request, res: Response) => {
  try {
    const updated = incidentService.updateIncident(req.params.id, req.body);
    if (!updated) {
      res.status(404).json({ error: "Incident not found" });
      return;
    }
    actionLog.record("UPDATE_INCIDENT", { id: updated.id, ...req.body }, false);
    res.json(updated);
  } catch (err: any) {
    console.error("[daedalus] /incidents/:id PATCH error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to update incident" });
  }
});

daedalusRouter.post("/incidents/:id/resolve", (req: Request, res: Response) => {
  try {
    const resolved = incidentService.resolveIncident(req.params.id);
    if (!resolved) {
      res.status(404).json({ error: "Incident not found" });
      return;
    }
    res.json(resolved);
  } catch (err: any) {
    console.error("[daedalus] /incidents/:id/resolve error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to resolve incident" });
  }
});

daedalusRouter.delete("/incidents/resolved", (_req: Request, res: Response) => {
  try {
    const cleared = incidentService.clearResolved();
    res.json({ cleared });
  } catch (err: any) {
    console.error("[daedalus] /incidents/resolved DELETE error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to clear resolved incidents" });
  }
});

// ── Action Log & Undo ─────────────────────────────────────────────────

daedalusRouter.get("/actions", (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string, 10) || 50;
    res.json(actionLog.list(limit));
  } catch (err: any) {
    console.error("[daedalus] /actions GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to list actions" });
  }
});

daedalusRouter.post("/actions/:id/undo", (req: Request, res: Response) => {
  try {
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
  } catch (err: any) {
    console.error("[daedalus] /actions/:id/undo error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to undo action" });
  }
});

// ── Chat ──────────────────────────────────────────────────────────────

daedalusRouter.post("/chat", (req: Request, res: Response) => {
  try {
    const text: string | undefined = req.body.message ?? req.body.content;
    const sessionId: string | undefined = req.body.sessionId;
    if (!text || typeof text !== "string" || !text.trim()) {
      res.status(400).json({ error: "Message content is required (send 'message' or 'content')" });
      return;
    }
    const { userMessage, daedalusMessage, response } = processMessage(text.trim(), sessionId);
    res.json({ userMessage, daedalusMessage, ...response });
  } catch (err: any) {
    console.error("[daedalus] /chat POST error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to process chat message" });
  }
});

daedalusRouter.get("/chat/help", (_req: Request, res: Response) => {
  try {
    res.json(getChatHelp());
  } catch (err: any) {
    console.error("[daedalus] /chat/help GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to get chat help" });
  }
});

daedalusRouter.get("/chat/history", (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string, 10) || 100;
    res.json(getChatHistory(limit));
  } catch (err: any) {
    console.error("[daedalus] /chat/history GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to fetch chat history" });
  }
});

daedalusRouter.delete("/chat/history", (req: Request, res: Response) => {
  try {
    const sessionId: string | undefined = req.body?.sessionId;
    clearChatHistory(sessionId);
    res.json({ cleared: true });
  } catch (err: any) {
    console.error("[daedalus] /chat/history DELETE error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to clear chat history" });
  }
});

daedalusRouter.get("/chat/welcome", (_req: Request, res: Response) => {
  try {
    res.json(getWelcomeMessage());
  } catch (err: any) {
    console.error("[daedalus] /chat/welcome GET error:", err?.message);
    res.status(500).json({ error: err?.message ?? "Failed to get welcome message" });
  }
});
