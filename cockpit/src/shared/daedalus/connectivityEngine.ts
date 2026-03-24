import type { ConnectivityNode, ConnectivitySnapshot, SuggestedTrustTier } from "./connectivity";

export interface RawNode {
  id: string;
  status: string;
  lastHeartbeat: string | null;
  risk: string;
  capabilities: { name: string }[];
}

const RISK_HEALTH: Record<string, number> = {
  low: 1,
  medium: 0.6,
  high: 0.2,
};

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

function deriveTrustTier(raw: RawNode): SuggestedTrustTier {
  if (raw.risk === "low" && raw.capabilities.length >= 2) return "high";
  if (raw.risk === "high") return "low";
  return "medium";
}

export function mapNode(raw: RawNode): ConnectivityNode {
  const capNames = Object.freeze(raw.capabilities.map((c) => c.name));
  return Object.freeze({
    id: raw.id,
    trusted: raw.status === "trusted",
    quarantined: raw.status === "quarantined",
    health: RISK_HEALTH[raw.risk] ?? 0.5,
    capabilityCount: raw.capabilities.length,
    capabilities: capNames,
    hasHeartbeat: raw.lastHeartbeat !== null,
    joinRequested: raw.status === "pending",
    suggestedTrustTier: deriveTrustTier(raw),
  });
}

export function computeConnectivity(
  rawNodes: readonly RawNode[],
  sseConnected: boolean,
): ConnectivitySnapshot {
  const nodes = rawNodes.map(mapNode);
  const total = nodes.length;

  if (total === 0) {
    return Object.freeze({
      nodes: Object.freeze(nodes),
      totalCount: 0,
      trustedCount: 0,
      quarantinedCount: 0,
      pendingJoinCount: 0,
      networkQuality: sseConnected ? 1 : 0.5,
      sseConnected,
    });
  }

  const trustedCount = nodes.filter((n) => n.trusted).length;
  const quarantinedCount = nodes.filter((n) => n.quarantined).length;
  const pendingJoinCount = nodes.filter((n) => n.joinRequested).length;
  const avgHealth = nodes.reduce((s, n) => s + n.health, 0) / total;
  const trustRatio = trustedCount / total;
  const ssePenalty = sseConnected ? 0 : 0.15;
  const networkQuality = clamp(avgHealth * 0.5 + trustRatio * 0.5 - ssePenalty);

  return Object.freeze({
    nodes: Object.freeze(nodes),
    totalCount: total,
    trustedCount,
    quarantinedCount,
    pendingJoinCount,
    networkQuality,
    sseConnected,
  });
}
