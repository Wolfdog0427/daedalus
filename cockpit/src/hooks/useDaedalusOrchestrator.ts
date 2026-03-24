import { useEffect, useState, useCallback, useRef } from "react";
import type {
  OrchestratorSnapshot,
  CapabilityTrace,
  NegotiationInput,
} from "../shared/daedalus/contracts";
import {
  fetchSnapshot,
  fetchCapabilityTrace,
  previewNegotiation,
  applyNegotiation,
} from "../api/daedalusClient";
import { useDaedalusEvents } from "./useDaedalusEvents";
import type { DaedalusEventPayload } from "./useDaedalusEvents";

const POLL_INTERVAL_MS = 5000;

export function useDaedalusOrchestrator() {
  const [snapshot, setSnapshot] = useState<OrchestratorSnapshot | null>(null);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [lastSnapshotAt, setLastSnapshotAt] = useState<Date | null>(null);

  const [selectedTrace, setSelectedTrace] = useState<CapabilityTrace | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);

  const [negotiationMessage, setNegotiationMessage] = useState<string | null>(null);
  const [loadingNegotiation, setLoadingNegotiation] = useState(false);

  const [highlightNodeId, setHighlightNodeId] = useState<string | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const { lastEvent: sseEvent, connected: sseConnected } = useDaedalusEvents();

  const loadSnapshot = useCallback(async () => {
    setLoadingSnapshot(true);
    setSnapshotError(null);
    try {
      const data = await fetchSnapshot();
      setSnapshot(data);
      setLastSnapshotAt(new Date());
    } catch (err: any) {
      setSnapshotError(err?.message ?? "Failed to load Daedalus snapshot.");
    } finally {
      setLoadingSnapshot(false);
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void loadSnapshot();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [loadSnapshot]);

  useEffect(() => {
    if (!sseEvent) return;
    void loadSnapshot();

    if (sseEvent.nodeId) {
      setHighlightNodeId(sseEvent.nodeId);
      clearTimeout(highlightTimer.current);
      highlightTimer.current = setTimeout(() => setHighlightNodeId(null), 1500);
    }
  }, [sseEvent, loadSnapshot]);

  const selectCapability = useCallback(async (nodeId: string, capabilityName: string) => {
    setLoadingTrace(true);
    setTraceError(null);
    setSelectedTrace(null);
    try {
      const trace = await fetchCapabilityTrace(nodeId, capabilityName);
      setSelectedTrace(trace);
    } catch (err: any) {
      setTraceError(err?.message ?? "Failed to load capability trace.");
    } finally {
      setLoadingTrace(false);
    }
  }, []);

  const toggleCapability = useCallback(
    async (nodeId: string, capabilityName: string, desiredEnabled: boolean) => {
      if (!snapshot) return;
      setLoadingNegotiation(true);
      setNegotiationMessage(null);
      try {
        const input: NegotiationInput = {
          requestedBy: { id: "operator" },
          targetNodeId: nodeId,
          capabilityName,
          desiredEnabled,
        };
        const preview = await previewNegotiation(input);
        const decision = preview.decisions[0];
        const applyResult = await applyNegotiation(input);
        setNegotiationMessage(
          applyResult.decisions[0]?.message ??
            decision?.message ??
            "Negotiation applied.",
        );
        await loadSnapshot();
      } catch (err: any) {
        setNegotiationMessage(err?.message ?? "Failed to apply negotiation.");
      } finally {
        setLoadingNegotiation(false);
      }
    },
    [snapshot, loadSnapshot],
  );

  return {
    snapshot,
    loadingSnapshot,
    snapshotError,
    lastSnapshotAt,
    selectedTrace,
    loadingTrace,
    traceError,
    negotiationMessage,
    loadingNegotiation,
    selectCapability,
    toggleCapability,
    reload: loadSnapshot,
    sseEvent,
    sseConnected,
    highlightNodeId,
  };
}
