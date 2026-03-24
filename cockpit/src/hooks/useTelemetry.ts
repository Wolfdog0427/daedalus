import { useEffect, useState, useCallback } from "react";
import { fetchTelemetry, type TelemetrySnapshot } from "../api/daedalusClient";
import { useDaedalusEvents } from "./useDaedalusEvents";
import type { DaedalusEventPayload } from "./useDaedalusEvents";

const POLL_MS = 12_000;

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchTelemetry();
      setTelemetry(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load telemetry");
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
        event.type === "ALIGNMENT_ESCALATION" ||
        event.type === "SAFE_MODE_ACTIVE" ||
        event.type === "ALIGNMENT_CONFIG_CHANGED"
      ) {
        void load();
      }
    }, [load]),
  );

  return { telemetry, error, loading, reload: load };
}
