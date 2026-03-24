import type {
  NodeMirror,
  NodeJoinPayload,
  NodeHeartbeatPayload,
  NodeCapSyncPayload,
  NodeExpressiveSyncPayload,
  NodeProfileSyncPayload,
  CapabilityDelta,
  ExpressiveDelta,
} from "./NodeMirror.types";
import type {
  NodeStatus,
  RiskTier,
  GlowLevel,
  DaedalusPosture,
  AttentionState,
} from "../../../shared/daedalus/contracts";

export interface CockpitNodeView {
  readonly id: string;
  readonly name: string;
  readonly status: NodeStatus;
  readonly risk: RiskTier;
  readonly phase: string;
  readonly kind: string;
  readonly glow: GlowLevel;
  readonly glowIntensity: number;
  readonly posture: DaedalusPosture;
  readonly attention: AttentionState;
  readonly continuity: string;
  readonly capabilities: string[];
  readonly heartbeatCount: number;
  readonly lastHeartbeatAt: string | null;
  readonly errorCount: number;
}
import {
  createFreshMirror,
  processJoin,
  processHeartbeat,
  processError,
  processQuarantine,
  processDetach,
} from "./NodeMirror.lifecycle";
import { processCapSync } from "./NodeMirror.capabilities";
import { processExpressiveSync, refreshExpressiveFromPhase } from "./NodeMirror.expressive";

export type MirrorEvent =
  | { type: "NODE_JOINED"; nodeId: string; mirror: NodeMirror }
  | { type: "NODE_HEARTBEAT"; nodeId: string; mirror: NodeMirror }
  | { type: "NODE_CAP_SYNCED"; nodeId: string; deltas: CapabilityDelta[] }
  | { type: "NODE_EXPRESSIVE_SYNCED"; nodeId: string; deltas: ExpressiveDelta[] }
  | { type: "NODE_PROFILE_SYNCED"; nodeId: string }
  | { type: "NODE_QUARANTINED"; nodeId: string; reason: string }
  | { type: "NODE_DETACHED"; nodeId: string }
  | { type: "NODE_ERROR"; nodeId: string; error: string }
  | { type: "NODE_STALE"; nodeId: string };

type MirrorListener = (event: MirrorEvent) => void;

export interface SafetyEnvelope {
  readonly errorQuarantineThreshold: number;
  readonly staleHeartbeatMs: number;
}

const DEFAULT_SAFETY_ENVELOPE: SafetyEnvelope = Object.freeze({
  errorQuarantineThreshold: 5,
  staleHeartbeatMs: 30_000,
});

export class NodeMirrorRegistry {
  private mirrors: Map<string, NodeMirror> = new Map();
  private listeners: Set<MirrorListener> = new Set();
  private safety: SafetyEnvelope = DEFAULT_SAFETY_ENVELOPE;

  configureSafety(envelope: Partial<SafetyEnvelope>): void {
    this.safety = { ...this.safety, ...envelope };
  }

  getSafety(): SafetyEnvelope {
    return this.safety;
  }

  subscribe(listener: MirrorListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  private emit(event: MirrorEvent) {
    for (const fn of this.listeners) {
      try { fn(event); } catch {}
    }
  }

  getMirror(id: string): NodeMirror | undefined {
    return this.mirrors.get(id);
  }

  getAllMirrors(): NodeMirror[] {
    return Array.from(this.mirrors.values());
  }

  handleJoin(payload: NodeJoinPayload): NodeMirror {
    let mirror = this.mirrors.get(payload.nodeId) ?? createFreshMirror(payload.nodeId);
    mirror = processJoin(mirror, payload);
    mirror = refreshExpressiveFromPhase(mirror);
    this.mirrors.set(payload.nodeId, mirror);
    this.emit({ type: "NODE_JOINED", nodeId: payload.nodeId, mirror });
    return mirror;
  }

  handleHeartbeat(payload: NodeHeartbeatPayload): NodeMirror | null {
    const mirror = this.mirrors.get(payload.nodeId);
    if (!mirror) return null;
    const updated = refreshExpressiveFromPhase(processHeartbeat(mirror, payload));
    this.mirrors.set(payload.nodeId, updated);
    this.emit({ type: "NODE_HEARTBEAT", nodeId: payload.nodeId, mirror: updated });
    return updated;
  }

  handleCapSync(payload: NodeCapSyncPayload): CapabilityDelta[] {
    const mirror = this.mirrors.get(payload.nodeId);
    if (!mirror) return [];
    const result = processCapSync(mirror, payload);
    this.mirrors.set(payload.nodeId, result.mirror);
    this.emit({ type: "NODE_CAP_SYNCED", nodeId: payload.nodeId, deltas: result.deltas });
    return result.deltas;
  }

  handleExpressiveSync(payload: NodeExpressiveSyncPayload): ExpressiveDelta[] {
    const mirror = this.mirrors.get(payload.nodeId);
    if (!mirror) return [];
    const result = processExpressiveSync(mirror, payload);
    this.mirrors.set(payload.nodeId, result.mirror);
    this.emit({ type: "NODE_EXPRESSIVE_SYNCED", nodeId: payload.nodeId, deltas: result.deltas });
    return result.deltas;
  }

  handleProfileSync(payload: NodeProfileSyncPayload): void {
    const mirror = this.mirrors.get(payload.nodeId);
    if (!mirror) return;
    const updated: NodeMirror = {
      ...mirror,
      profile: { ...payload.profile },
      lifecycle: { ...mirror.lifecycle, lastProfileSync: payload.timestamp },
    };
    this.mirrors.set(payload.nodeId, updated);
    this.emit({ type: "NODE_PROFILE_SYNCED", nodeId: payload.nodeId });
  }

  handleQuarantine(nodeId: string, reason: string = "Operator-initiated quarantine"): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;
    if (mirror.lifecycle.phase === "quarantined" || mirror.lifecycle.phase === "detached") return;
    const updated = refreshExpressiveFromPhase(processQuarantine(mirror));
    this.mirrors.set(nodeId, updated);
    this.emit({ type: "NODE_QUARANTINED", nodeId, reason });
  }

  handleDetach(nodeId: string): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;
    processDetach(mirror);
    this.emit({ type: "NODE_DETACHED", nodeId });
    this.mirrors.delete(nodeId);
  }

  handleError(nodeId: string, error: string): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;

    const errored = processError(mirror, error);
    this.mirrors.set(nodeId, errored);
    this.emit({ type: "NODE_ERROR", nodeId, error });

    if (
      errored.lifecycle.errorCount >= this.safety.errorQuarantineThreshold &&
      errored.lifecycle.phase !== "quarantined" &&
      errored.lifecycle.phase !== "detached"
    ) {
      this.handleQuarantine(nodeId, `Error count ${errored.lifecycle.errorCount} exceeded threshold ${this.safety.errorQuarantineThreshold}`);
    }
  }

  /**
   * Sweep all mirrors for stale heartbeats. Nodes whose last heartbeat
   * is older than `staleHeartbeatMs` and are still active/degraded get
   * marked offline via an error event. Call this periodically.
   */
  sweepStaleHeartbeats(nowMs: number = Date.now()): string[] {
    const stale: string[] = [];

    for (const mirror of this.mirrors.values()) {
      const phase = mirror.lifecycle.phase;
      if (phase !== "active" && phase !== "degraded") continue;

      const lastHb = mirror.lifecycle.lastHeartbeat;
      if (!lastHb) continue;

      const age = nowMs - new Date(lastHb).getTime();
      if (age > this.safety.staleHeartbeatMs) {
        stale.push(mirror.id);
        this.handleError(mirror.id, `Stale heartbeat: ${Math.round(age / 1000)}s since last`);
        this.emit({ type: "NODE_STALE", nodeId: mirror.id });
      }
    }

    return stale;
  }

  getCount(): number {
    return this.mirrors.size;
  }

  toCockpitView(): CockpitNodeView[] {
    const views: CockpitNodeView[] = [];

    for (const mirror of this.mirrors.values()) {
      const cont = mirror.expressive.continuity;
      const continuityLabel = cont.healthy
        ? (cont.streak > 0 ? `healthy (streak ${cont.streak})` : "healthy")
        : "degraded";

      views.push({
        id: mirror.id,
        name: mirror.name,
        status: mirror.status,
        risk: mirror.risk,
        phase: mirror.lifecycle.phase,
        kind: mirror.profile.kind,
        glow: mirror.expressive.glow.level,
        glowIntensity: mirror.expressive.glow.intensity,
        posture: mirror.expressive.posture,
        attention: mirror.expressive.attention,
        continuity: continuityLabel,
        capabilities: mirror.capabilities.entries.map(c => c.name),
        heartbeatCount: mirror.lifecycle.heartbeatCount,
        lastHeartbeatAt: mirror.lifecycle.lastHeartbeat,
        errorCount: mirror.lifecycle.errorCount,
      });
    }

    return views;
  }
}

let singleton: NodeMirrorRegistry | null = null;
let bridgeUnsub: (() => void) | null = null;

export function getNodeMirrorRegistry(): NodeMirrorRegistry {
  if (!singleton) {
    singleton = new NodeMirrorRegistry();
    bridgeMirrorToBus(singleton);
  }
  return singleton;
}

export function resetNodeMirrorRegistry(): void {
  if (bridgeUnsub) { bridgeUnsub(); bridgeUnsub = null; }
  singleton = null;
}

function bridgeMirrorToBus(registry: NodeMirrorRegistry): void {
  const { getDaedalusEventBus, nowIso } = require("../DaedalusEventBus");
  const bus = getDaedalusEventBus();

  bridgeUnsub = registry.subscribe((event) => {
    const ts = nowIso();
    switch (event.type) {
      case "NODE_JOINED":
        bus.publish({ type: "MIRROR_NODE_JOINED", timestamp: ts, nodeId: event.nodeId, mirrorPhase: event.mirror.lifecycle.phase, mirrorStatus: event.mirror.status, summary: `Node "${event.nodeId}" joined` });
        break;
      case "NODE_HEARTBEAT":
        bus.publish({ type: "MIRROR_NODE_HEARTBEAT", timestamp: ts, nodeId: event.nodeId, mirrorPhase: event.mirror.lifecycle.phase, mirrorStatus: event.mirror.status });
        break;
      case "NODE_CAP_SYNCED":
        bus.publish({
          type: "MIRROR_NODE_CAP_SYNCED",
          timestamp: ts,
          nodeId: event.nodeId,
          summary: `${event.deltas.length} capability delta${event.deltas.length === 1 ? "" : "s"}`,
        });
        break;
      case "NODE_EXPRESSIVE_SYNCED":
        bus.publish({ type: "MIRROR_NODE_EXPRESSIVE_SYNCED", timestamp: ts, nodeId: event.nodeId });
        break;
      case "NODE_PROFILE_SYNCED":
        bus.publish({ type: "MIRROR_NODE_PROFILE_SYNCED", timestamp: ts, nodeId: event.nodeId });
        break;
      case "NODE_QUARANTINED":
        bus.publish({ type: "MIRROR_NODE_QUARANTINED", timestamp: ts, nodeId: event.nodeId, summary: event.reason });
        break;
      case "NODE_DETACHED":
        bus.publish({ type: "MIRROR_NODE_DETACHED", timestamp: ts, nodeId: event.nodeId });
        break;
      case "NODE_ERROR":
        bus.publish({ type: "MIRROR_NODE_ERROR", timestamp: ts, nodeId: event.nodeId, summary: event.error });
        break;
      case "NODE_STALE":
        bus.publish({ type: "MIRROR_NODE_STALE", timestamp: ts, nodeId: event.nodeId });
        break;
    }
  });
}
