import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { NotificationItem } from '../api/types';

const POLL_INTERVAL = 6_000;

export function NotificationsPanel() {
  const [data, setData] = useState<NotificationItem[] | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getNotifications();
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

  const items = data ? [...data].reverse() : [];

  return (
    <div className="panel panel-wide">
      <div className="panel-title">Notifications</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && items.length === 0 && <div className="empty">No notifications yet</div>}
      {items.length > 0 && (
        <ul className="event-list">
          {items.slice(0, 20).map((n) => (
            <li key={n.id} className="event-item">
              <span className="event-type">{n.type}</span>
              <span className="event-time">
                {new Date(n.timestamp).toLocaleTimeString()}
              </span>
              <div className="event-payload">
                {JSON.stringify(n.payload).slice(0, 120)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
