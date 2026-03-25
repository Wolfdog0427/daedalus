import { useEffect, useState, useCallback } from "react";
import {
  fetchCockpitNodes,
  fetchCockpitSummary,
  type CockpitNodeView,
  type CockpitSummary,
} from "../api/daedalusClient";
import "./CockpitNodeListPanel.css";

const POLL_MS = 2_000;

function formatHeartbeat(iso: string | null): string {
  if (!iso) return "never";
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}

export function CockpitNodeListPanel() {
  const [nodes, setNodes] = useState<CockpitNodeView[]>([]);
  const [summary, setSummary] = useState<CockpitSummary | null>(null);
  const [error, setError] = useState<string>();

  const poll = useCallback(async (signal: AbortSignal) => {
    try {
      const [n, s] = await Promise.all([fetchCockpitNodes(), fetchCockpitSummary()]);
      if (!signal.aborted) {
        setNodes(n);
        setSummary(s);
        setError(undefined);
      }
    } catch (err) {
      if (!signal.aborted) {
        setError(err instanceof Error ? err.message : "Unreachable");
      }
    }
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    void poll(ac.signal);
    const id = setInterval(() => void poll(ac.signal), POLL_MS);
    return () => {
      ac.abort();
      clearInterval(id);
    };
  }, [poll]);

  return (
    <div className="panel panel-wide">
      <div className="panel-title">Cockpit &mdash; Node Cortex</div>

      {error && <div className="error-msg">{error}</div>}
      {!summary && !error && <div className="loading">Connecting&hellip;</div>}

      {summary && (
        <div className="cockpit-summary">
          <Stat value={summary.totalNodes} label="nodes" />
          {Object.entries(summary.byStatus).map(([k, v]) => (
            <Stat key={`s-${k}`} value={v} label={k} />
          ))}
          {Object.entries(summary.byPosture).map(([k, v]) => (
            <Stat key={`p-${k}`} value={v} label={k} color="var(--accent)" />
          ))}
          {Object.entries(summary.byRisk).map(([k, v]) => (
            <Stat key={`r-${k}`} value={v} label={`risk:${k}`}
              color={k === "high" ? "var(--red)" : k === "medium" ? "var(--yellow)" : undefined} />
          ))}
          {summary.totalErrors > 0 && (
            <Stat value={summary.totalErrors} label="errors" color="var(--red)" />
          )}
        </div>
      )}

      {nodes.length === 0 && summary && (
        <div className="empty">No nodes registered yet. Nodes will appear here after joining via the mirror API. Capabilities and traces populate once nodes sync their capabilities.</div>
      )}

      <div className="cockpit-nodes">
        <div className="cockpit-card-list">
          {nodes.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label, color }: { value: number; label: string; color?: string }) {
  return (
    <div className="cockpit-stat">
      <span className="cockpit-stat-val" style={color ? { color } : undefined}>
        {value}
      </span>
      <span className="cockpit-stat-label">{label}</span>
    </div>
  );
}

function NodeCard({ node }: { node: CockpitNodeView }) {
  return (
    <div className="cockpit-card">
      <div className={`cockpit-glow cockpit-glow--${node.glow}`} />

      <div className="cockpit-identity">
        <div className="cockpit-name">{node.name}</div>
        <div className="cockpit-meta">
          {node.id} &middot; {node.kind} &middot; {node.phase}
        </div>
      </div>

      <span className={`cockpit-posture cockpit-posture--${node.posture}`}>
        {node.posture}
      </span>

      <span className={`cockpit-status cockpit-status--${node.status}`}>
        {node.status}
      </span>

      <span className={`cockpit-risk cockpit-risk--${node.risk}`}>
        {node.risk}
      </span>

      <div className="cockpit-detail">
        <span className="cockpit-continuity">{node.continuity}</span>
        <div className="cockpit-caps">
          {node.capabilities.slice(0, 3).map((cap) => (
            <span key={cap} className="cockpit-cap-chip">{cap}</span>
          ))}
          {node.capabilities.length > 3 && (
            <span className="cockpit-cap-chip">+{node.capabilities.length - 3}</span>
          )}
        </div>
      </div>

      <div className="cockpit-card-tail">
        {node.errorCount > 0 && (
          <span className="cockpit-error-count">{node.errorCount} err</span>
        )}
        <span className="cockpit-heartbeat">
          {formatHeartbeat(node.lastHeartbeatAt)}
        </span>
      </div>
    </div>
  );
}
