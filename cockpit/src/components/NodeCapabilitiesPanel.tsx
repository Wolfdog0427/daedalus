import './NodeCapabilitiesPanel.css';

interface CapabilityInfo {
  name: string;
  value: string;
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
}

function NodeCapabilitiesPanel({ nodes = [], highlightNodeId, onCapabilityClick }: Props) {
  return (
    <div className="panel">
      <h2>Node Capabilities</h2>

      <div className="node-grid">
        {nodes.map((node) => (
          <div
            key={node.id}
            className={`node-card glow-${node.glow} risk-${node.risk}${highlightNodeId === node.id ? ' node-card--pulse' : ''}`}
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
              {node.capabilities.length === 0 && (
                <p className="empty">None</p>
              )}
              {node.capabilities.map((cap) => (
                <div
                  key={cap.name}
                  className="cap-row cap-row-clickable"
                  onClick={() => onCapabilityClick?.(node.id, cap.name)}
                >
                  <span className="cap-name">{cap.name}</span>
                  <span className="cap-value">{cap.value}</span>
                </div>
              ))}
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
