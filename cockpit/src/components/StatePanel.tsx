import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { StateResponse } from '../api/types';

const POLL_INTERVAL = 8_000;

export function StatePanel() {
  const [data, setData] = useState<StateResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getState();
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

  // Hook: render richer system/meta details later

  return (
    <div className="panel">
      <div className="panel-title">State</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && (
        <>
          <div className="kv">
            <span className="kv-key">Posture</span>
            <span className="kv-val">{data.posture?.mode ?? '—'}</span>
          </div>
          <div className="kv">
            <span className="kv-key">Events</span>
            <span className="kv-val">{data.state?.events?.length ?? 0}</span>
          </div>
          <div className="kv">
            <span className="kv-key">Nodes</span>
            <span className="kv-val">
              {Object.keys(data.presence?.nodes ?? {}).length}
            </span>
          </div>
          <div className="kv">
            <span className="kv-key">Threads</span>
            <span className="kv-val">
              {Object.keys(data.continuity?.threads ?? {}).length}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
