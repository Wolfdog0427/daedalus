import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { CapabilityItem } from '../api/types';

const POLL_INTERVAL = 10_000;

export function CapabilitiesPanel() {
  const [data, setData] = useState<CapabilityItem[] | null>(null);
  const [error, setError] = useState<string>();
  const [toggling, setToggling] = useState<string>();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await apiClient.getCapabilities();
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

  const handleToggle = useCallback(async (cap: CapabilityItem) => {
    setToggling(cap.name);
    try {
      const updated = await apiClient.patchCapability(cap.name, !cap.enabled);
      setData((prev) =>
        prev ? prev.map((c) => (c.name === updated.name ? updated : c)) : prev,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Toggle failed');
    } finally {
      setToggling(undefined);
    }
  }, []);

  return (
    <div className="panel">
      <div className="panel-title">Capabilities</div>
      {error && <div className="error-msg">{error}</div>}
      {!data && !error && <div className="loading">Loading…</div>}
      {data && data.length === 0 && <div className="empty">None registered</div>}
      {data && data.length > 0 && (
        <ul className="event-list">
          {data.map((cap) => (
            <li key={cap.name} className="event-item cap-row">
              <div className="cap-info">
                <span className="event-type">{cap.name}</span>
                <div className="event-payload">{cap.description}</div>
              </div>
              <button
                className={`cap-toggle ${cap.enabled ? 'cap-toggle-on' : 'cap-toggle-off'}`}
                disabled={toggling === cap.name}
                onClick={() => handleToggle(cap)}
              >
                {cap.enabled ? 'On' : 'Off'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
