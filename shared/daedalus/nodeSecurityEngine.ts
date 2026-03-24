import {
  NodeJoinProposal,
  NodeJoinDecision,
  JoinDecisionKind,
  DeviceFingerprint,
  NodeRiskTier,
} from './nodeContracts';

export interface SecurityContext {
  readonly knownFingerprints: readonly DeviceFingerprint[];
  readonly recentAnomalies: readonly string[];
  readonly networkTrust: 'trusted' | 'untrusted' | 'unknown';
}

/**
 * Fingerprint match: device ID + model must match a known entry.
 * OS or version drift triggers re-verification.
 */
export function matchFingerprint(
  fingerprint: DeviceFingerprint,
  known: readonly DeviceFingerprint[],
): 'exact' | 'drift' | 'unknown' {
  const match = known.find(fp => fp.deviceId === fingerprint.deviceId);
  if (!match) return 'unknown';
  if (match.model === fingerprint.model &&
      match.os === fingerprint.os &&
      match.osVersion === fingerprint.osVersion) {
    return 'exact';
  }
  return 'drift';
}

/**
 * Compute a risk tier for an incoming proposal based on security signals.
 * High risk signals (>2) or unknown network → HIGH.
 * Drifted fingerprint or any anomalies → MEDIUM.
 * Otherwise → LOW.
 */
export function assessProposalRisk(
  proposal: NodeJoinProposal,
  ctx: SecurityContext,
): NodeRiskTier {
  if (proposal.initialRiskSignals.length > 2) return NodeRiskTier.HIGH;
  if (ctx.networkTrust === 'untrusted') return NodeRiskTier.HIGH;
  if (ctx.recentAnomalies.length > 0) return NodeRiskTier.MEDIUM;

  const fpMatch = matchFingerprint(proposal.fingerprint, ctx.knownFingerprints);
  if (fpMatch === 'unknown') return NodeRiskTier.MEDIUM;
  if (fpMatch === 'drift') return NodeRiskTier.MEDIUM;

  return NodeRiskTier.LOW;
}

/**
 * Determine whether a join proposal requires additional verification
 * (biometric, second factor, or explicit operator approval).
 * Conditions:
 * - Unknown fingerprint
 * - Drifted fingerprint
 * - High risk signals
 * - Untrusted network
 * - Recent anomalies present
 */
export function requiresAdditionalVerification(
  proposal: NodeJoinProposal,
  ctx: SecurityContext,
): boolean {
  const fpMatch = matchFingerprint(proposal.fingerprint, ctx.knownFingerprints);
  if (fpMatch !== 'exact') return true;
  if (proposal.initialRiskSignals.length > 0) return true;
  if (ctx.networkTrust === 'untrusted') return true;
  if (ctx.recentAnomalies.length > 0) return true;
  return false;
}

/**
 * Apply security gate to a join proposal and produce a decision.
 * This is the primary security entry point for node joins.
 */
export function securityGateJoinProposal(
  proposal: NodeJoinProposal,
  ctx: SecurityContext,
): NodeJoinDecision {
  const risk = assessProposalRisk(proposal, ctx);
  const needsVerification = requiresAdditionalVerification(proposal, ctx);
  const now = Date.now();

  if (risk === NodeRiskTier.HIGH || needsVerification) {
    return Object.freeze({
      nodeId: proposal.nodeId,
      decision: JoinDecisionKind.NEEDS_OPERATOR_APPROVAL,
      reason: `Security gate: risk=${risk}, verification=${needsVerification}`,
      decidedAt: now,
    });
  }

  return Object.freeze({
    nodeId: proposal.nodeId,
    decision: JoinDecisionKind.APPROVED,
    reason: 'Security gate passed: known device, low risk, trusted network',
    decidedAt: now,
  });
}
