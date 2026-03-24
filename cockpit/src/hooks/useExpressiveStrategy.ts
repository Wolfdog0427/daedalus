import { useState, useEffect, useRef, useCallback } from "react";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { OperatorIntent } from "../shared/daedalus/intentModel";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyProposal, AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import type {
  ExpressiveStrategy,
  StrategyEvalState,
} from "../shared/daedalus/expressiveStrategy";
import {
  STRATEGY_ENABLED,
  STRATEGY_EVAL_IDLE,
  STRATEGY_DEFAULTS,
} from "../shared/daedalus/expressiveStrategy";
import {
  evolveStrategy,
  evaluateStrategy,
} from "../shared/daedalus/expressiveStrategyEngine";

export interface StrategyModelState {
  evalState: StrategyEvalState;
  approvedStrategy: ExpressiveStrategy | null;
  pending: AutonomyProposal | null;
  approvedTuning: AdaptationTuning;
  decisions: AutonomyDecision[];
  approve: (proposalId: number) => void;
  reject: (proposalId: number) => void;
  clearTuning: () => void;
}

const EVAL_INTERVAL_MS = 5000;

/**
 * Tracks long-arc operator interaction patterns, builds confidence
 * in a candidate strategy, and produces Tier-3 autonomy proposals
 * when the pattern is sustained long enough.
 *
 * Uses refs for live analytics/intent values so the evaluation
 * interval is only restarted when the pending state changes.
 */
export function useExpressiveStrategy(
  analytics: AnalyticsSnapshot,
  currentIntent: OperatorIntent | null,
): StrategyModelState {
  const strategyRef = useRef<StrategyEvalState>(STRATEGY_EVAL_IDLE);
  const lastProposalRef = useRef(0);
  const idRef = useRef(0);
  const analyticsRef = useRef(analytics);
  analyticsRef.current = analytics;
  const intentRef = useRef(currentIntent);
  intentRef.current = currentIntent;

  const [evalState, setEvalState] = useState<StrategyEvalState>(STRATEGY_EVAL_IDLE);
  const [approvedStrategy, setApprovedStrategy] = useState<ExpressiveStrategy | null>(null);
  const [pending, setPending] = useState<AutonomyProposal | null>(null);
  const [approvedTuning, setApprovedTuning] = useState<AdaptationTuning>({});
  const [decisions, setDecisions] = useState<AutonomyDecision[]>([]);

  useEffect(() => {
    if (!STRATEGY_ENABLED) return;

    const interval = setInterval(() => {
      const now = Date.now();

      if (pending) {
        // Continue evolving confidence but don't propose while one is pending
        strategyRef.current = evolveStrategy(
          strategyRef.current,
          intentRef.current,
          analyticsRef.current,
          STRATEGY_DEFAULTS,
          now,
        );
        setEvalState({ ...strategyRef.current });
        return;
      }

      const result = evaluateStrategy(
        strategyRef.current,
        intentRef.current,
        analyticsRef.current,
        lastProposalRef.current,
        ++idRef.current,
        STRATEGY_DEFAULTS,
        now,
      );

      strategyRef.current = result.state;
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
      const candidate = strategyRef.current.candidate;
      setApprovedStrategy(candidate);
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
    setApprovedStrategy(null);
  }, []);

  return {
    evalState,
    approvedStrategy,
    pending,
    approvedTuning,
    decisions,
    approve,
    reject,
    clearTuning,
  };
}
