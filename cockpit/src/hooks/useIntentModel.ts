import { useState, useEffect, useRef, useCallback } from "react";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyProposal, AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import type { OperatorIntent, IntentSignal } from "../shared/daedalus/intentModel";
import { INTENT_MODEL_ENABLED, INTENT_MODEL_DEFAULTS } from "../shared/daedalus/intentModel";
import {
  evaluateIntent,
  trimSignals,
  inferIntent,
} from "../shared/daedalus/intentModelEngine";

export interface IntentModelState {
  currentIntent: OperatorIntent | null;
  signalCount: number;
  pending: AutonomyProposal | null;
  approvedTuning: AdaptationTuning;
  decisions: AutonomyDecision[];
  approve: (proposalId: number) => void;
  reject: (proposalId: number) => void;
  clearTuning: () => void;
}

const THROTTLE_MS = 300;
const EVAL_INTERVAL_MS = 3000;

/**
 * Records operator interaction signals (keystrokes, clicks, focus,
 * visibility changes), infers the current interaction mode, and
 * produces Tier-1 autonomy proposals when a clear pattern emerges.
 *
 * Proposals reuse the same `AutonomyProposal` shape as Tier-0
 * and carry `AdaptationTuning` as their recommended changes.
 */
export function useIntentModel(): IntentModelState {
  const signalsRef = useRef<IntentSignal[]>([]);
  const lastProposalRef = useRef(0);
  const idRef = useRef(0);
  const lastSignalRef = useRef(0);

  const [currentIntent, setCurrentIntent] = useState<OperatorIntent | null>(null);
  const [signalCount, setSignalCount] = useState(0);
  const [pending, setPending] = useState<AutonomyProposal | null>(null);
  const [approvedTuning, setApprovedTuning] = useState<AdaptationTuning>({});
  const [decisions, setDecisions] = useState<AutonomyDecision[]>([]);

  useEffect(() => {
    if (!INTENT_MODEL_ENABLED) return;

    const record = (type: IntentSignal["type"]) => {
      const now = Date.now();
      if (now - lastSignalRef.current < THROTTLE_MS) return;
      lastSignalRef.current = now;
      signalsRef.current.push({ timestamp: now, type });
    };

    const onKeydown = () => record("input");
    const onClick = () => record("navigation");
    const onFocus = () => record("focus");
    const onVisibility = () => {
      if (document.hidden) record("idle");
    };

    window.addEventListener("keydown", onKeydown);
    window.addEventListener("click", onClick);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      window.removeEventListener("keydown", onKeydown);
      window.removeEventListener("click", onClick);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  // Periodic evaluation — keep `pending` in deps so the interval
  // restarts when a proposal is approved/rejected, resuming evaluation.
  useEffect(() => {
    if (!INTENT_MODEL_ENABLED) return;

    const interval = setInterval(() => {
      const now = Date.now();
      signalsRef.current = trimSignals(signalsRef.current, INTENT_MODEL_DEFAULTS.windowMs, now);
      setSignalCount(signalsRef.current.length);

      const intent = inferIntent(signalsRef.current, INTENT_MODEL_DEFAULTS);
      setCurrentIntent(intent);

      if (pending) return;

      const result = evaluateIntent(
        signalsRef.current,
        lastProposalRef.current,
        ++idRef.current,
        INTENT_MODEL_DEFAULTS,
        now,
      );

      if (result) {
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

  return {
    currentIntent,
    signalCount,
    pending,
    approvedTuning,
    decisions,
    approve,
    reject,
    clearTuning,
  };
}
