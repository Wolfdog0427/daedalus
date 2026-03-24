import { useEffect, useState, useCallback } from "react";
import { fetchStrategy, type StrategyResponse } from "../api/daedalusClient";
import { useDaedalusEvents } from "./useDaedalusEvents";
import type { DaedalusEventPayload } from "./useDaedalusEvents";

const POLL_MS = 8_000;

export function useStrategy() {
  const [evaluation, setEvaluation] = useState<StrategyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchStrategy();
      setEvaluation(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load strategy");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  useDaedalusEvents(
    useCallback((event: DaedalusEventPayload) => {
      if (
        event.type === "STRATEGY_CHANGED" ||
        event.type === "POSTURE_CHANGED" ||
        event.type === "GOVERNANCE_OVERRIDE_APPLIED" ||
        event.type === "CONTINUITY_DRIFT_DETECTED" ||
        event.type === "BEING_PRESENCE_UPDATED" ||
        event.type === "ALIGNMENT_ESCALATION" ||
        event.type === "SAFE_MODE_ACTIVE" ||
        event.type === "ALIGNMENT_CONFIG_CHANGED" ||
        event.type === "CHANGE_AUTO_APPROVED" ||
        event.type === "CHANGE_REQUIRES_REVIEW" ||
        event.type === "REGULATION_MACRO_FIRED" ||
        event.type === "REGULATION_SAFE_MODE_SIGNAL" ||
        event.type === "CHANGE_REGISTERED" ||
        event.type === "CHANGE_ROLLED_BACK" ||
        event.type === "CHANGE_ACCEPTED" ||
        event.type === "OPERATOR_BOUND" ||
        event.type === "OPERATOR_UNBOUND" ||
        event.type === "OPERATOR_TRUST_SUSPICIOUS" ||
        event.type === "OPERATOR_HIGH_RISK_DENIED" ||
        event.type === "CONSTITUTIONAL_FREEZE_CHANGED"
      ) {
        void load();
      }
    }, [load]),
  );

  return { evaluation, error, loading, reload: load };
}
