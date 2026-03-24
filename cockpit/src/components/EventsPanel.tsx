import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { StateResponse } from '../api/types';

const POLL_INTERVAL = 6_000;

interface EventEntry {
  type: string;
  payload?: any;
  meta?: Record<string, any>;
}

export function EventsPanel() {
  const [events, setEvents] = useState<EventEntry[]>([]);
  const [error, setError] = useState<string>();
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res: StateResponse = await apiClient.getState();
        if (active) {
          setEvents(res.state?.events ?? []);
          setError(undefined);
          setLoaded(true);
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

  // Hook: support filtering by event type later

  const sorted = [...events].reverse();

  return (
    <div className="panel">
      <div className="panel-title">Events</div>
      {error && <div className="error-msg">{error}</div>}
      {!loaded && !error && <div className="loading">Loading…</div>}
      {loaded && sorted.length === 0 && (
        <div className="empty">No events yet</div>
      )}
      <ul className="event-list">
        {sorted.map((ev, i) => (
          <li key={`${ev.type}-${i}`} className="event-item">
            <span className="event-type">{ev.type}</span>
            {ev.meta?.issuedAt && (
              <span className="event-time">
                {new Date(ev.meta.issuedAt).toLocaleTimeString()}
              </span>
            )}
            <div className="event-payload">
              {compactPayload(ev.payload)}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function compactPayload(payload: unknown): string {
  const json = JSON.stringify(payload);
  return json.length > 120 ? json.slice(0, 120) + '…' : json;
}
