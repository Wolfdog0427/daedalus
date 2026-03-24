import { useCallback, useState } from "react";
import { previewNegotiation, applyNegotiation } from "../api/daedalusClient";
import "./NodeCapabilitiesPanel.css";

interface CapabilityInfo {
  name: string;
  value: string;
  enabled?: boolean;
}

interface NodeInfo {
  id: string;
  status: string;
  lastHeartbeat: string | null;
  glow: "none" | "low" | "medium" | "high";
  risk: "low" | "medium" | "high";
  capabilities: CapabilityInfo[];
}

interface Props {
  nodes?: NodeInfo[];
  highlightNodeId?: string | null;
  onCapabilityClick?: (nodeId: string, capabilityName: string) => void;
  onNegotiationApplied?: () => void;
}

function capabilityIsEnabled(cap: CapabilityInfo): boolean {
  if (typeof cap.enabled === "boolean") return cap.enabled;
  return cap.value.toLowerCase() === "enabled";
}

function NodeCapabilitiesPanel({
  nodes = [],
  highlightNodeId,
  onCapabilityClick,
  onNegotiationApplied,
}: Props) {
  const [negotiatingKey, setNegotiatingKey] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  const runNegotiation = useCallback(
    async (nodeId: string, cap: CapabilityInfo) => {
      const key = `${nodeId}:${cap.name}`;
      setNegotiatingKey(key);
      setFeedback(null);
      const desiredEnabled = !capabilityIsEnabled(cap);
      const input = {
        requestedBy: { id: "operator" },
        targetNodeId: nodeId,
        capabilityName: cap.name,
        desiredEnabled,
      };
      try {
        const preview = await previewNegotiation(input);
        const previewText = preview.decisions.map((d) => d.message).join("\n");
        if (!window.confirm(`Preview:\n\n${previewText}\n\nApply this change?`)) {
          return;
        }
        const result = await applyNegotiation(input);
        const resultText =
          result.decisions.map((d) => d.message).join("\n") || "Negotiation finished.";
        setFeedback({ ok: true, text: resultText });
        onNegotiationApplied?.();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Negotiation failed.";
        setFeedback({ ok: false, text: msg });
      } finally {
        setNegotiatingKey(null);
      }
    },
    [onNegotiationApplied],
  );

  return (
    <div className="panel">
      <h2>Node Capabilities</h2>
      {feedback && (
        <div
          className={`negotiation-feedback negotiation-feedback--${feedback.ok ? "ok" : "err"}`}
        >
          {feedback.text}
        </div>
      )}

      <div className="node-grid">
        {nodes.map((node) => (
          <div
            key={node.id}
            className={`node-card glow-${node.glow} risk-${node.risk}${highlightNodeId === node.id ? " node-card--pulse" : ""}`}
          >
            <header className="node-header">
              <span className="node-id">{node.id}</span>
              <span className={`node-status status-${node.status.toLowerCase()}`}>
                {node.status}
              </span>
            </header>

            <div className="node-meta">
              <div className="meta-row">
                <label>Glow</label>
                <span>{node.glow}</span>
              </div>

              <div className="meta-row">
                <label>Risk</label>
                <span>{node.risk}</span>
              </div>

              <div className="meta-row">
                <label>Last heartbeat</label>
                <span>
                  {node.lastHeartbeat
                    ? new Date(node.lastHeartbeat).toLocaleTimeString()
                    : "—"}
                </span>
              </div>
            </div>

            <div className="capabilities">
              <h4>Capabilities</h4>
              {node.capabilities.length === 0 && <p className="empty">None</p>}
              {node.capabilities.map((cap) => {
                const negKey = `${node.id}:${cap.name}`;
                const busy = negotiatingKey === negKey;
                return (
                  <div
                    key={cap.name}
                    className="cap-row cap-row-clickable"
                    onClick={() => onCapabilityClick?.(node.id, cap.name)}
                  >
                    <span className="cap-name-group">
                      <button
                        type="button"
                        className="cap-negotiate-btn"
                        title="Negotiate capability (toggle)"
                        disabled={busy}
                        onClick={(e) => {
                          e.stopPropagation();
                          void runNegotiation(node.id, cap);
                        }}
                      >
                        {busy ? "…" : "🔀"}
                      </button>
                      <span className="cap-name">{cap.name}</span>
                    </span>
                    <span className="cap-value">{cap.value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export type { NodeInfo, CapabilityInfo };
export { NodeCapabilitiesPanel };
export default NodeCapabilitiesPanel;
