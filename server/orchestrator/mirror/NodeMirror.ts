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
  | { type: "NODE_QUARANTINED"; nodeId: string }
  | { type: "NODE_DETACHED"; nodeId: string }
  | { type: "NODE_ERROR"; nodeId: string; error: string };

type MirrorListener = (event: MirrorEvent) => void;

export class NodeMirrorRegistry {
  private mirrors: Map<string, NodeMirror> = new Map();
  private listeners: Set<MirrorListener> = new Set();

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

  handleQuarantine(nodeId: string): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;
    const updated = refreshExpressiveFromPhase(processQuarantine(mirror));
    this.mirrors.set(nodeId, updated);
    this.emit({ type: "NODE_QUARANTINED", nodeId });
  }

  handleDetach(nodeId: string): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;
    const updated = processDetach(mirror);
    this.mirrors.set(nodeId, updated);
    this.emit({ type: "NODE_DETACHED", nodeId });
  }

  handleError(nodeId: string, error: string): void {
    const mirror = this.mirrors.get(nodeId);
    if (!mirror) return;
    this.mirrors.set(nodeId, processError(mirror, error));
    this.emit({ type: "NODE_ERROR", nodeId, error });
  }

  getCount(): number {
    return this.mirrors.size;
  }
}

let singleton: NodeMirrorRegistry | null = null;

export function getNodeMirrorRegistry(): NodeMirrorRegistry {
  if (!singleton) singleton = new NodeMirrorRegistry();
  return singleton;
}

export function resetNodeMirrorRegistry(): void {
  singleton = null;
}
