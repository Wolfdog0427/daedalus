import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { RiskResponse } from '../api/types';

const POLL_INTERVAL = 8_000;

const TIER_BADGE: Record<string, string> = {
  low: 'badge-ok',
  medium: 'badge-warn',
  elevated: 'badge-elevated',
  critical: 'badge-error',
};

export function RiskPanel() {
  const [data, setData] = useState<RiskResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getRisk();
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
      <div className="panel-title">Risk & Verification</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && (
        <>
          <div className="kv">
            <span className="kv-key">Risk tier</span>
            <span className={`badge ${TIER_BADGE[data.risk.tier] ?? ''}`}>
              {data.risk.tier}
            </span>
          </div>
          <div className="kv">
            <span className="kv-key">Verification</span>
            <span className="kv-val">{data.verification.requirement}</span>
          </div>
          {data.risk.factors.length > 0 && (
            <div className="kv">
              <span className="kv-key">Factors</span>
              <span className="kv-val">{data.risk.factors.join(', ')}</span>
            </div>
          )}
          {data.verification.lastEvent && (
            <div className="kv">
              <span className="kv-key">Last verified</span>
              <span className="kv-val">
                {new Date(data.verification.lastEvent.timestamp).toLocaleString()}
                {' '}({data.verification.lastEvent.method})
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
