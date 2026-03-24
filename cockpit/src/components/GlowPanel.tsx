import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { GlowResponse } from '../api/types';

const POLL_INTERVAL = 4_000;

export function GlowPanel() {
  const [data, setData] = useState<GlowResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getGlow();
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
      <div className="panel-title">Expressive Glow</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && (
        <>
          <div
            className="glow-indicator"
            style={{
              background: data.hue,
              opacity: data.intensity,
              height: 8,
              borderRadius: 4,
              marginBottom: 12,
            }}
          />
          <div className="kv">
            <span className="kv-key">State</span>
            <span className="kv-val">{data.label}</span>
          </div>
          <div className="kv">
            <span className="kv-key">Hue</span>
            <span className="kv-val">{data.hue}</span>
          </div>
          <div className="kv">
            <span className="kv-key">Intensity</span>
            <span className="kv-val">{data.intensity.toFixed(2)}</span>
          </div>
        </>
      )}
    </div>
  );
}
