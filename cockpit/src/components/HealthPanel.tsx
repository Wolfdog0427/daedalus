import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { HealthResponse } from '../api/types';

const POLL_INTERVAL = 8_000;

export function HealthPanel() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getHealth();
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

  return (
    <div className="panel">
      <div className="panel-title">Health</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && (
        <>
          <div className="kv">
            <span className="kv-key">Status</span>
            <span className={`badge ${data.status === 'ok' ? 'badge-ok' : 'badge-error'}`}>
              {data.status}
            </span>
          </div>
          <div className="kv">
            <span className="kv-key">Version</span>
            <span className="kv-val">{data.version}</span>
          </div>
          <div className="kv">
            <span className="kv-key">Posture</span>
            <span className="kv-val">{data.posture.mode}</span>
          </div>
          {data.risk && (
            <div className="kv">
              <span className="kv-key">Risk</span>
              <span className="kv-val">{data.risk}</span>
            </div>
          )}
          {data.posture.reason && (
            <div className="kv">
              <span className="kv-key">Reason</span>
              <span className="kv-val">{data.posture.reason}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
