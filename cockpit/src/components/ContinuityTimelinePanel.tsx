import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { TimelineResponse } from '../api/types';

const POLL_INTERVAL = 8_000;

export function ContinuityTimelinePanel() {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getTimeline();
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

  const entries = data?.entries ?? [];
  const reversed = [...entries].reverse();

  return (
    <div className="panel panel-wide">
      <div className="panel-title">Continuity Timeline</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && data.threadIds.length > 0 && (
        <div style={{ marginBottom: 8, fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          Threads: {data.threadIds.join(', ')}
        </div>
      )}
      {data && reversed.length === 0 && (
        <div className="empty">No timeline entries yet</div>
      )}
      {reversed.length > 0 && (
        <ul className="event-list">
          {reversed.slice(0, 50).map((entry, i) => (
            <li key={i} className="event-item">
              <span className="event-type">{entry.type}</span>
              <span className="event-time">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
              {entry.postureAtTime && (
                <span className="badge badge-warn" style={{ marginLeft: 8 }}>
                  posture: {entry.postureAtTime}
                </span>
              )}
              {entry.summary && (
                <div className="event-payload">{entry.summary}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
