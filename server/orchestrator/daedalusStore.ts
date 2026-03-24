import {
  CapabilityReasonCode,
  CapabilityTrace,
  CapabilityTraceStep,
  NegotiationApplyResult,
  NegotiationDecision,
  NegotiationInput,
  NegotiationPreview,
  OrchestratorSnapshot,
  BeingPresenceDetail,
} from "../../shared/daedalus/contracts";
import { getDaedalusEventBus, nowIso as eventNowIso } from "./DaedalusEventBus";
import { getNodeMirrorRegistry } from "./mirror/NodeMirror";

const nowIso = () => new Date().toISOString();

class DaedalusStore {
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
  }

  getSnapshot(): OrchestratorSnapshot {
    const registry = getNodeMirrorRegistry();
    const views = registry.toCockpitView();
    const nodes = views.map((v) => ({
      id: v.id,
      status: v.status as any,
      lastHeartbeat: v.lastHeartbeatAt ?? nowIso(),
      glow: v.glow as any,
      risk: v.risk as any,
      capabilities: v.capabilities.map((name) => ({
        name,
        value: "enabled",
        enabled: true,
      })),
    }));
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

  getCapabilityTrace(nodeId: string, capabilityName: string): CapabilityTrace | null {
    const registry = getNodeMirrorRegistry();
    const mirror = registry.getMirror(nodeId);
    if (!mirror) return null;

    const cap = mirror.capabilities.entries.find((c) => c.name === capabilityName);
    const steps: CapabilityTraceStep[] = [];

    if (!cap) {
      steps.push({
        level: "orchestrator",
        sourceId: "core-orchestrator",
        reason: "NOT_PRESENT",
        message: `Capability "${capabilityName}" is not present on node "${nodeId}".`,
        timestamp: nowIso(),
      });
      return { nodeId, capabilityName, effectiveEnabled: false, steps };
    }

    steps.push({
      level: "node",
      sourceId: nodeId,
      reason: cap.enabled ? ("NOT_PRESENT" as CapabilityReasonCode) : "NODE_VETO",
      message: cap.enabled
        ? `Node "${nodeId}" has capability "${capabilityName}" enabled at node level.`
        : `Node "${nodeId}" has capability "${capabilityName}" disabled.`,
      timestamp: nowIso(),
    });

    if (mirror.risk === "high") {
      steps.push({
        level: "orchestrator",
        sourceId: "core-orchestrator",
        reason: "RISK_ESCALATION",
        message: `High risk tier for node "${nodeId}" may constrain capability "${capabilityName}".`,
        timestamp: nowIso(),
      });
    }

    steps.push({
      level: "governance",
      sourceId: "governance-engine",
      reason: "NOT_PRESENT",
      message: "No explicit governance override recorded for this capability in the current snapshot.",
      timestamp: nowIso(),
    });

    return { nodeId, capabilityName, effectiveEnabled: cap.enabled, steps };
  }

  previewNegotiation(input: NegotiationInput): NegotiationPreview | null {
    const registry = getNodeMirrorRegistry();
    const mirror = registry.getMirror(input.targetNodeId);
    if (!mirror) return null;

    const existing = mirror.capabilities.entries.find((c) => c.name === input.capabilityName);
    const fromEnabled = existing ? existing.enabled : false;
    const toEnabled = input.desiredEnabled;

    const reason: CapabilityReasonCode | null = fromEnabled === toEnabled ? null : "NODE_VETO";
    const message =
      fromEnabled === toEnabled
        ? `No change: capability "${input.capabilityName}" already ${fromEnabled ? "enabled" : "disabled"}.`
        : `Capability "${input.capabilityName}" would change from ${fromEnabled ? "enabled" : "disabled"} to ${toEnabled ? "enabled" : "disabled"} for node "${mirror.id}".`;

    return {
      nodeId: mirror.id,
      requestedBy: input.requestedBy,
      decisions: [{ capabilityName: input.capabilityName, fromEnabled, toEnabled, reason, message }],
    };
  }

  applyNegotiation(input: NegotiationInput): NegotiationApplyResult | null {
    const registry = getNodeMirrorRegistry();
    const mirror = registry.getMirror(input.targetNodeId);
    if (!mirror) return null;

    let cap = mirror.capabilities.entries.find((c) => c.name === input.capabilityName);
    const fromEnabled = cap ? cap.enabled : false;
    const toEnabled = input.desiredEnabled;

    if (!cap) {
      mirror.capabilities.entries.push({ name: input.capabilityName, value: toEnabled ? "enabled" : "disabled", enabled: toEnabled });
    } else {
      cap.enabled = toEnabled;
      cap.value = toEnabled ? "enabled" : "disabled";
    }

    const bus = getDaedalusEventBus();
    const reason: CapabilityReasonCode | null = fromEnabled === toEnabled ? null : "NODE_VETO";
    const message =
      fromEnabled === toEnabled
        ? `No change applied: capability "${input.capabilityName}" already ${fromEnabled ? "enabled" : "disabled"}.`
        : `Applied change: capability "${input.capabilityName}" from ${fromEnabled ? "enabled" : "disabled"} to ${toEnabled ? "enabled" : "disabled"} on node "${mirror.id}".`;

    if (fromEnabled !== toEnabled) {
      bus.publish({ type: "NEGOTIATION_COMPLETED", timestamp: eventNowIso(), nodeId: mirror.id, summary: message });
    }

    return {
      nodeId: mirror.id,
      applied: fromEnabled !== toEnabled,
      decisions: [{ capabilityName: input.capabilityName, fromEnabled, toEnabled, reason, message }],
    };
  }

  // ── Being Presence ─────────────────────────────────────────────────

  getBeingPresences(): BeingPresenceDetail[] {
    return Array.from(this.beingPresences.values());
  }

  getBeingPresence(beingId: string): BeingPresenceDetail | undefined {
    return this.beingPresences.get(beingId);
  }

  addBeingPresence(being: BeingPresenceDetail): void {
    this.beingPresences.set(being.id, being);
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
