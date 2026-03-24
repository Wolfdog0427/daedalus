import { useState, useEffect, useRef, useCallback } from "react";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { ExpressiveStrategy } from "../shared/daedalus/expressiveStrategy";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyProposal, AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import type {
  MetaStrategy,
  MetaStrategyEvalState,
} from "../shared/daedalus/metaStrategy";
import {
  META_STRATEGY_ENABLED,
  META_STRATEGY_EVAL_IDLE,
  META_STRATEGY_DEFAULTS,
} from "../shared/daedalus/metaStrategy";
import {
  recordStrategy,
  evolveMetaStrategy,
  evaluateMetaStrategy,
} from "../shared/daedalus/metaStrategyEngine";

export interface MetaStrategyModelState {
  evalState: MetaStrategyEvalState;
  approvedMeta: MetaStrategy | null;
  pending: AutonomyProposal | null;
  approvedTuning: AdaptationTuning;
  decisions: AutonomyDecision[];
  approve: (proposalId: number) => void;
  reject: (proposalId: number) => void;
  clearTuning: () => void;
}

const EVAL_INTERVAL_MS = 8000;

/**
 * Observes the stream of Tier-3 strategy approvals, maintains a
 * rolling history window, infers meta-level patterns, and produces
 * Tier-4 autonomy proposals when a sustained meta-strategy emerges.
 *
 * The hook records each new `approvedStrategy` from Tier-3 into
 * its history, then periodically evaluates meta-strategy confidence.
 */
export function useMetaStrategy(
  analytics: AnalyticsSnapshot,
  approvedStrategy: ExpressiveStrategy | null,
): MetaStrategyModelState {
  const stateRef = useRef<MetaStrategyEvalState>(META_STRATEGY_EVAL_IDLE);
  const lastProposalRef = useRef(0);
  const idRef = useRef(0);
  const analyticsRef = useRef(analytics);
  analyticsRef.current = analytics;
  const prevStrategyRef = useRef<ExpressiveStrategy | null>(null);

  const [evalState, setEvalState] = useState<MetaStrategyEvalState>(META_STRATEGY_EVAL_IDLE);
  const [approvedMeta, setApprovedMeta] = useState<MetaStrategy | null>(null);
  const [pending, setPending] = useState<AutonomyProposal | null>(null);
  const [approvedTuning, setApprovedTuning] = useState<AdaptationTuning>({});
  const [decisions, setDecisions] = useState<AutonomyDecision[]>([]);

  // Record new Tier-3 strategy approvals into history
  useEffect(() => {
    if (!META_STRATEGY_ENABLED) return;
    if (approvedStrategy && approvedStrategy !== prevStrategyRef.current) {
      prevStrategyRef.current = approvedStrategy;
      stateRef.current = {
        ...stateRef.current,
        history: recordStrategy(
          stateRef.current.history,
          approvedStrategy,
          META_STRATEGY_DEFAULTS.historyWindowMs,
        ),
      };
    }
  }, [approvedStrategy]);

  // Periodic evaluation
  useEffect(() => {
    if (!META_STRATEGY_ENABLED) return;

    const interval = setInterval(() => {
      const now = Date.now();

      if (pending) {
        stateRef.current = evolveMetaStrategy(
          stateRef.current,
          analyticsRef.current,
          META_STRATEGY_DEFAULTS,
          now,
        );
        setEvalState({ ...stateRef.current });
        return;
      }

      const result = evaluateMetaStrategy(
        stateRef.current,
        analyticsRef.current,
        lastProposalRef.current,
        ++idRef.current,
        META_STRATEGY_DEFAULTS,
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
      setApprovedMeta(stateRef.current.candidate);
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
    setApprovedMeta(null);
  }, []);

  return {
    evalState,
    approvedMeta,
    pending,
    approvedTuning,
    decisions,
    approve,
    reject,
    clearTuning,
  };
}
