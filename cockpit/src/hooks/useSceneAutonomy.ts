import { useState, useEffect, useRef, useCallback } from "react";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyProposal, AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import { SCENE_AUTONOMY_ENABLED, AUTONOMY_DEFAULTS } from "../shared/daedalus/sceneAutonomy";
import { evaluateAutonomy } from "../shared/daedalus/sceneAutonomyEngine";

export interface AutonomyState {
  pending: AutonomyProposal | null;
  approvedTuning: AdaptationTuning;
  decisions: AutonomyDecision[];
  approve: (proposalId: number) => void;
  reject: (proposalId: number) => void;
  clearTuning: () => void;
}

/**
 * Evaluates analytics against autonomy thresholds and manages
 * the proposal/decision lifecycle. Proposals are rate-limited
 * and only one can be pending at a time.
 *
 * Approved tuning persists until explicitly cleared or
 * overwritten by a newer approved proposal.
 */
export function useSceneAutonomy(analytics: AnalyticsSnapshot): AutonomyState {
  const [pending, setPending] = useState<AutonomyProposal | null>(null);
  const [approvedTuning, setApprovedTuning] = useState<AdaptationTuning>({});
  const [decisions, setDecisions] = useState<AutonomyDecision[]>([]);
  const lastProposalRef = useRef(0);
  const idRef = useRef(0);

  useEffect(() => {
    if (!SCENE_AUTONOMY_ENABLED) return;
    if (pending) return; // don't propose while one is pending

    const proposal = evaluateAutonomy(
      analytics,
      lastProposalRef.current,
      ++idRef.current,
      AUTONOMY_DEFAULTS,
    );

    if (proposal) {
      lastProposalRef.current = proposal.timestamp;
      setPending(proposal);
    }
  });

  const approve = useCallback(
    (proposalId: number) => {
      if (!pending || pending.id !== proposalId) return;
      setApprovedTuning(pending.recommended);
      setDecisions((prev) => [
        ...prev.slice(-19),
        { proposalId, approved: true, timestamp: Date.now() },
      ]);
      setPending(null);
    },
    [pending],
  );

  const reject = useCallback(
    (proposalId: number) => {
      if (!pending || pending.id !== proposalId) return;
      setDecisions((prev) => [
        ...prev.slice(-19),
        { proposalId, approved: false, timestamp: Date.now() },
      ]);
      setPending(null);
    },
    [pending],
  );

  const clearTuning = useCallback(() => {
    setApprovedTuning({});
  }, []);

  return { pending, approvedTuning, decisions, approve, reject, clearTuning };
}
