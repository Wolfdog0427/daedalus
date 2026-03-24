import { useState, useEffect, useRef, useCallback } from "react";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { ExpressiveStrategy } from "../shared/daedalus/expressiveStrategy";
import type { MetaStrategy } from "../shared/daedalus/metaStrategy";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyProposal, AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import type {
  MetaGovernanceIssue,
  MetaGovernanceEvalState,
} from "../shared/daedalus/metaGovernance";
import {
  META_GOVERNANCE_ENABLED,
  META_GOVERNANCE_EVAL_IDLE,
  META_GOVERNANCE_DEFAULTS,
} from "../shared/daedalus/metaGovernance";
import {
  evolveGovernance,
  evaluateGovernance,
} from "../shared/daedalus/metaGovernanceEngine";

export interface MetaGovernanceModelState {
  evalState: MetaGovernanceEvalState;
  approvedIssue: MetaGovernanceIssue | null;
  pending: AutonomyProposal | null;
  approvedTuning: AdaptationTuning;
  decisions: AutonomyDecision[];
  approve: (proposalId: number) => void;
  reject: (proposalId: number) => void;
  clearTuning: () => void;
}

const EVAL_INTERVAL_MS = 10000;

/**
 * Observes the expressive system's analytics, the active Tier-3
 * strategy, and the active Tier-4 meta-strategy to detect systemic
 * issues. Produces Tier-5 autonomy proposals when an issue is
 * sustained with sufficient confidence.
 */
export function useMetaGovernance(
  analytics: AnalyticsSnapshot,
  activeStrategy: ExpressiveStrategy | null,
  activeMeta: MetaStrategy | null,
): MetaGovernanceModelState {
  const stateRef = useRef<MetaGovernanceEvalState>(META_GOVERNANCE_EVAL_IDLE);
  const lastProposalRef = useRef(0);
  const idRef = useRef(0);
  const analyticsRef = useRef(analytics);
  analyticsRef.current = analytics;
  const strategyRef = useRef(activeStrategy);
  strategyRef.current = activeStrategy;
  const metaRef = useRef(activeMeta);
  metaRef.current = activeMeta;

  const [evalState, setEvalState] = useState<MetaGovernanceEvalState>(META_GOVERNANCE_EVAL_IDLE);
  const [approvedIssue, setApprovedIssue] = useState<MetaGovernanceIssue | null>(null);
  const [pending, setPending] = useState<AutonomyProposal | null>(null);
  const [approvedTuning, setApprovedTuning] = useState<AdaptationTuning>({});
  const [decisions, setDecisions] = useState<AutonomyDecision[]>([]);

  useEffect(() => {
    if (!META_GOVERNANCE_ENABLED) return;

    const interval = setInterval(() => {
      const now = Date.now();

      if (pending) {
        stateRef.current = evolveGovernance(
          stateRef.current,
          analyticsRef.current,
          strategyRef.current,
          metaRef.current,
          META_GOVERNANCE_DEFAULTS,
          now,
        );
        setEvalState({ ...stateRef.current });
        return;
      }

      const result = evaluateGovernance(
        stateRef.current,
        analyticsRef.current,
        strategyRef.current,
        metaRef.current,
        lastProposalRef.current,
        ++idRef.current,
        META_GOVERNANCE_DEFAULTS,
        now,
      );

      stateRef.current = result.state;
      setEvalState({ ...result.state });

      if (result.proposal) {
        lastProposalRef.current = result.proposal.timestamp;
        setPending(result.proposal);
      }
    }, EVAL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [pending]);

  const approve = useCallback(
    (proposalId: number) => {
      if (!pending || pending.id !== proposalId) return;
      setApprovedTuning(pending.recommended);
      setApprovedIssue(stateRef.current.candidate);
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
    setApprovedIssue(null);
  }, []);

  return {
    evalState,
    approvedIssue,
    pending,
    approvedTuning,
    decisions,
    approve,
    reject,
    clearTuning,
  };
}
