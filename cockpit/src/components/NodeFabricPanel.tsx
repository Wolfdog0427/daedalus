import React from 'react';
import { NodeSummary, NodeId, NodeStatus } from '../shared/daedalus/nodeContracts';
import { NodeNotification } from '../shared/daedalus/nodeNotifications';
import './NodeFabricPanel.css';

interface Props {
  readonly nodes: readonly NodeSummary[];
  readonly notifications: readonly NodeNotification[];
  readonly onApprove: (nodeId: NodeId) => void;
  readonly onReject: (nodeId: NodeId) => void;
  readonly onQuarantine: (nodeId: NodeId) => void;
  readonly onDetach: (nodeId: NodeId) => void;
}

export const NodeFabricPanel: React.FC<Props> = ({
  nodes,
  notifications,
  onApprove,
  onReject,
  onQuarantine,
  onDetach,
}) => (
  <div className="node-fabric">
    <div className="node-fabric-title">Node Fabric</div>

    <div className="node-fabric-list">
      {nodes.length === 0 && (
        <span className="node-fabric-empty">No nodes registered</span>
      )}

      {nodes.map(node => (
        <div className="node-fabric-card" key={node.nodeId}>
          <div className={`node-fabric-glow node-fabric-glow--${node.posture}`} />

          <div className="node-fabric-info">
            <div className="node-fabric-id">{node.nodeId}</div>
            <div className="node-fabric-meta">
              {node.kind} &middot; {node.batteryBand} &middot; {node.connectivityBand}
            </div>
          </div>

          <span className={`node-fabric-status node-fabric-status--${node.status}`}>
            {node.status}
          </span>

          <div className="node-fabric-actions">
            {node.status === NodeStatus.PENDING && (
              <>
                <button
                  className="node-fabric-action node-fabric-action--approve"
                  onClick={() => onApprove(node.nodeId)}
                >
                  Approve
                </button>
                <button
                  className="node-fabric-action node-fabric-action--reject"
                  onClick={() => onReject(node.nodeId)}
                >
                  Reject
                </button>
              </>
            )}
            {(node.status === NodeStatus.ACTIVE || node.status === NodeStatus.DEGRADED) && (
              <>
                <button
                  className="node-fabric-action"
                  onClick={() => onQuarantine(node.nodeId)}
                >
                  Quarantine
                </button>
                <button
                  className="node-fabric-action"
                  onClick={() => onDetach(node.nodeId)}
                >
                  Detach
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>

    {notifications.length > 0 && (
      <div className="node-fabric-notif">
        <div className="node-fabric-notif-title">Notifications ({notifications.length})</div>
        {notifications.slice(-5).map(n => (
          <div key={n.id} className={`node-fabric-notif-card node-fabric-notif-card--${n.type}`}>
            <strong>{n.type.replace(/_/g, ' ')}</strong>: {n.nodeDescription}
            {n.riskSummary && <> &mdash; {n.riskSummary}</>}
          </div>
        ))}
      </div>
    )}
  </div>
);
