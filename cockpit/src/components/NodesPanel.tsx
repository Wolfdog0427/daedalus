import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { NodesResponse } from '../api/types';

const POLL_INTERVAL = 8_000;

export function NodesPanel() {
  const [data, setData] = useState<NodesResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getNodes();
        if (active) {
          setData(res);
          setError(undefined);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Unreachable');
      }
    }

    void poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const nodes = data ? Object.values(data.nodes) : [];

  return (
    <div className="panel">
      <div className="panel-title">Node Registry</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && nodes.length === 0 && (
        <div className="empty">No nodes registered</div>
      )}
      {nodes.length > 0 && (
        <ul className="event-list">
          {nodes.map((node) => (
            <li key={node.id} className="event-item">
              <div>
                <span className="event-type">{node.id}</span>
                <span className="event-time">
                  last seen {new Date(node.lastHeartbeat).toLocaleTimeString()}
                </span>
              </div>
              {node.capabilities.length > 0 && (
                <div className="event-payload">
                  capabilities: {node.capabilities.join(', ')}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && (
        <div className="kv" style={{ marginTop: 8 }}>
          <span className="kv-key">Total</span>
          <span className="kv-val">{data.count}</span>
        </div>
      )}
    </div>
  );
}
