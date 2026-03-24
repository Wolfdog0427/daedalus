import {
  Capability,
  CapabilityReasonCode,
  CapabilityTrace,
  CapabilityTraceStep,
  GlowLevel,
  NegotiationApplyResult,
  NegotiationDecision,
  NegotiationInput,
  NegotiationPreview,
  NodePresence,
  NodeStatus,
  OrchestratorSnapshot,
  RiskTier,
  BeingPresenceDetail,
} from "../../shared/daedalus/contracts";
import { getDaedalusEventBus, nowIso as eventNowIso } from "./DaedalusEventBus";

const nowIso = () => new Date().toISOString();

class DaedalusStore {
  private nodes: Map<string, NodePresence> = new Map();
  private beingPresences: Map<string, BeingPresenceDetail> = new Map();

  constructor() {
    this.seed();
  }

  private seed() {
    this.beingPresences.set("operator", {
      id: "operator",
      name: "Operator",
      posture: "companion",
      glow: { level: "high", intensity: 0.85 },
      attention: { level: "focused" },
      heartbeat: Date.now(),
      influenceLevel: 0.9,
      presenceMode: "active",
      isSpeaking: false,
      isGuiding: true,
      continuity: { streak: 12, lastCheckIn: nowIso(), healthy: true },
      autopilot: { enabled: false, scope: "none" },
      updatedAt: nowIso(),
    });

    this.beingPresences.set("guardian-1", {
      id: "guardian-1",
      name: "Guardian Alpha",
      posture: "sentinel",
      glow: { level: "medium", intensity: 0.5 },
      attention: { level: "aware" },
      heartbeat: Date.now(),
      influenceLevel: 0.4,
      presenceMode: "ambient",
      isSpeaking: false,
      isGuiding: false,
      continuity: { streak: 7, lastCheckIn: nowIso(), healthy: true },
      autopilot: { enabled: true, scope: "local" },
      updatedAt: nowIso(),
    });

    const seedNodes: NodePresence[] = [
      {
        id: "core-orchestrator",
        status: "trusted",
        lastHeartbeat: nowIso(),
        glow: "high",
        risk: "low",
        capabilities: [
          { name: "negotiation", value: "enabled", enabled: true },
          { name: "capability-trace", value: "enabled", enabled: true },
          { name: "node-registry", value: "enabled", enabled: true },
        ],
      },
      {
        id: "perception-node-1",
        status: "pending",
        lastHeartbeat: nowIso(),
        glow: "medium",
        risk: "medium",
        capabilities: [
          { name: "vision", value: "enabled", enabled: true },
          { name: "audio", value: "disabled", enabled: false },
        ],
      },
    ];

    seedNodes.forEach((n) => this.nodes.set(n.id, n));
  }

  getSnapshot(): OrchestratorSnapshot {
    const nodes = Array.from(this.nodes.values());
    return {
      nodes,
      beings: [
        {
          id: "operator",
          label: "Operator",
          nodes: nodes.map((n) => n.id),
          dominantGlow: "high",
          dominantRisk: "low",
        },
      ],
    };
  }

  getNodes(): NodePresence[] {
    return Array.from(this.nodes.values());
  }

  getNode(nodeId: string): NodePresence | undefined {
    return this.nodes.get(nodeId);
  }

  private computeRiskForNode(node: NodePresence): RiskTier {
    // Simple heuristic: high risk if any disabled capability with "security" in name.
    const hasSecurityDisable = node.capabilities.some(
      (c) => !c.enabled && c.name.toLowerCase().includes("security"),
    );
    if (hasSecurityDisable) return "high";
    if (node.status === "pending") return "medium";
    return node.risk;
  }

  private computeGlowForNode(node: NodePresence): GlowLevel {
    if (node.status === "trusted") return "high";
    if (node.status === "pending") return "medium";
    if (node.status === "quarantined") return "low";
    return node.glow;
  }

  getCapabilityTrace(nodeId: string, capabilityName: string): CapabilityTrace | null {
    const node = this.nodes.get(nodeId);
    if (!node) return null;

    const cap = node.capabilities.find((c) => c.name === capabilityName);
    const steps: CapabilityTraceStep[] = [];

    if (!cap) {
      steps.push({
        level: "orchestrator",
        sourceId: "core-orchestrator",
        reason: "NOT_PRESENT",
        message: `Capability "${capabilityName}" is not present on node "${nodeId}".`,
        timestamp: nowIso(),
      });

      return {
        nodeId,
        capabilityName,
        effectiveEnabled: false,
        steps,
      };
    }

    // Node-level state
    if (!cap.enabled) {
      steps.push({
        level: "node",
        sourceId: nodeId,
        reason: "NODE_VETO",
        message: `Node "${nodeId}" has capability "${capabilityName}" disabled.`,
        timestamp: nowIso(),
      });
    } else {
      steps.push({
        level: "node",
        sourceId: nodeId,
        reason: "NOT_PRESENT",
        message: `Node "${nodeId}" has capability "${capabilityName}" enabled at node level.`,
        timestamp: nowIso(),
      });
    }

    // Risk escalation
    const risk = this.computeRiskForNode(node);
    if (risk === "high") {
      steps.push({
        level: "orchestrator",
        sourceId: "core-orchestrator",
        reason: "RISK_ESCALATION",
        message: `High risk tier for node "${nodeId}" may constrain capability "${capabilityName}".`,
        timestamp: nowIso(),
      });
    }

    // Governance / continuity placeholders
    steps.push({
      level: "governance",
      sourceId: "governance-engine",
      reason: "NOT_PRESENT",
      message:
        "No explicit governance override recorded for this capability in the current snapshot.",
      timestamp: nowIso(),
    });

    return {
      nodeId,
      capabilityName,
      effectiveEnabled: cap.enabled,
      steps,
    };
  }

  previewNegotiation(input: NegotiationInput): NegotiationPreview | null {
    const node = this.nodes.get(input.targetNodeId);
    if (!node) return null;

    const existing = node.capabilities.find(
      (c) => c.name === input.capabilityName,
    );

    const fromEnabled = existing ? existing.enabled : false;
    const toEnabled = input.desiredEnabled;

    const reason: CapabilityReasonCode | null =
      fromEnabled === toEnabled ? null : "NODE_VETO";

    const message =
      fromEnabled === toEnabled
        ? `No change: capability "${input.capabilityName}" already ${
            fromEnabled ? "enabled" : "disabled"
          }.`
        : `Capability "${input.capabilityName}" would change from ${
            fromEnabled ? "enabled" : "disabled"
          } to ${toEnabled ? "enabled" : "disabled"} for node "${node.id}".`;

    const decision: NegotiationDecision = {
      capabilityName: input.capabilityName,
      fromEnabled,
      toEnabled,
      reason,
      message,
    };

    return {
      nodeId: node.id,
      requestedBy: input.requestedBy,
      decisions: [decision],
    };
  }

  applyNegotiation(input: NegotiationInput): NegotiationApplyResult | null {
    const node = this.nodes.get(input.targetNodeId);
    if (!node) return null;

    let cap = node.capabilities.find((c) => c.name === input.capabilityName);
    const fromEnabled = cap ? cap.enabled : false;
    const toEnabled = input.desiredEnabled;

    if (!cap) {
      cap = {
        name: input.capabilityName,
        value: toEnabled ? "enabled" : "disabled",
        enabled: toEnabled,
      };
      node.capabilities.push(cap);
    } else {
      cap.enabled = toEnabled;
      cap.value = toEnabled ? "enabled" : "disabled";
    }

    node.lastHeartbeat = nowIso();
    const prevRisk = node.risk;
    const prevGlow = node.glow;
    node.risk = this.computeRiskForNode(node);
    node.glow = this.computeGlowForNode(node);

    const bus = getDaedalusEventBus();

    if (node.glow !== prevGlow) {
      bus.publish({
        type: "NODE_GLOW_UPDATED",
        timestamp: eventNowIso(),
        nodeId: node.id,
        glow: node.glow,
      });
    }

    if (node.risk !== prevRisk) {
      bus.publish({
        type: "NODE_RISK_UPDATED",
        timestamp: eventNowIso(),
        nodeId: node.id,
        risk: node.risk,
      });
    }

    const reason: CapabilityReasonCode | null =
      fromEnabled === toEnabled ? null : "NODE_VETO";

    const message =
      fromEnabled === toEnabled
        ? `No change applied: capability "${input.capabilityName}" already ${
            fromEnabled ? "enabled" : "disabled"
          }.`
        : `Applied change: capability "${input.capabilityName}" from ${
            fromEnabled ? "enabled" : "disabled"
          } to ${toEnabled ? "enabled" : "disabled"} on node "${node.id}".`;

    const decision: NegotiationDecision = {
      capabilityName: input.capabilityName,
      fromEnabled,
      toEnabled,
      reason,
      message,
    };

    this.nodes.set(node.id, node);

    if (fromEnabled !== toEnabled) {
      bus.publish({
        type: "NEGOTIATION_COMPLETED",
        timestamp: eventNowIso(),
        nodeId: node.id,
        summary: message,
      });
    }

    return {
      nodeId: node.id,
      applied: fromEnabled !== toEnabled,
      decisions: [decision],
    };
  }

  // ── Being Presence ─────────────────────────────────────────────────

  getBeingPresences(): BeingPresenceDetail[] {
    return Array.from(this.beingPresences.values());
  }

  getBeingPresence(beingId: string): BeingPresenceDetail | undefined {
    return this.beingPresences.get(beingId);
  }

  updateBeingPresence(
    beingId: string,
    patch: Partial<Omit<BeingPresenceDetail, "id" | "updatedAt">>,
  ): BeingPresenceDetail | null {
    const existing = this.beingPresences.get(beingId);
    if (!existing) return null;

    const updated: BeingPresenceDetail = {
      ...existing,
      ...patch,
      id: existing.id,
      updatedAt: nowIso(),
    };
    this.beingPresences.set(beingId, updated);

    getDaedalusEventBus().publish({
      type: "BEING_PRESENCE_UPDATED",
      timestamp: eventNowIso(),
      beingId: updated.id,
      beingPresence: updated,
      summary: `Being "${updated.name}" presence updated`,
    });

    return updated;
  }
}

export const daedalusStore = new DaedalusStore();
