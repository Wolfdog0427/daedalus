import type { ConnectivitySnapshot } from "./connectivity";
import type { EpistemicReport } from "./epistemicIntake";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

/**
 * Derives an epistemic health report from the connectivity snapshot.
 *
 * Quality is penalized by quarantined nodes, low trust ratio, and
 * SSE disconnection. The report is purely diagnostic — it never
 * feeds back into governance or autonomy logic.
 */
/**
 * Knowledge freshness: ratio of nodes that have a recent heartbeat.
 * Nodes without a heartbeat are considered stale.
 */
function computeFreshness(nodes: ConnectivitySnapshot["nodes"]): number {
  if (nodes.length === 0) return 1;
  const freshCount = nodes.filter((n) => n.hasHeartbeat).length;
  return clamp(freshCount / nodes.length);
}

/**
 * Count of unverified nodes — nodes that are neither trusted nor
 * quarantined and lack a heartbeat. These represent unknown-provenance
 * data sources the operator should be aware of.
 */
function countUnverified(nodes: ConnectivitySnapshot["nodes"]): number {
  return nodes.filter(
    (n) => !n.trusted && !n.quarantined && !n.hasHeartbeat,
  ).length;
}

export function computeEpistemicReport(
  connectivity: ConnectivitySnapshot,
): EpistemicReport {
  const { totalCount, trustedCount, quarantinedCount, nodes, sseConnected, networkQuality } =
    connectivity;

  if (totalCount === 0) {
    return Object.freeze({
      overallQuality: sseConnected ? 0.8 : 0.5,
      trustedRatio: 1,
      quarantinedRatio: 0,
      connectivityPenalty: sseConnected ? 0 : 0.2,
      healthy: sseConnected,
      freshness: sseConnected ? 1 : 0,
      unverifiedCount: 0,
      unverifiedWarning: false,
    });
  }

  const trustedRatio = trustedCount / totalCount;
  const quarantinedRatio = quarantinedCount / totalCount;

  const quarantinePenalty = quarantinedRatio * 0.4;
  const trustBonus = trustedRatio * 0.3;
  const connectivityPenalty = sseConnected ? 0 : 0.2;

  const overallQuality = clamp(
    networkQuality + trustBonus - quarantinePenalty - connectivityPenalty,
  );

  const healthy = overallQuality >= 0.5 && quarantinedRatio < 0.5;

  const freshness = computeFreshness(nodes);
  const unverifiedCount = countUnverified(nodes);
  const unverifiedWarning = unverifiedCount > 0;

  return Object.freeze({
    overallQuality,
    trustedRatio,
    quarantinedRatio,
    connectivityPenalty,
    healthy,
    freshness,
    unverifiedCount,
    unverifiedWarning,
  });
}
