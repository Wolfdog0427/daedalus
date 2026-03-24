import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { CapabilityProfile } from '../api/types';

export function ProfilesPanel() {
  const [profiles, setProfiles] = useState<CapabilityProfile[] | null>(null);
  const [error, setError] = useState<string>();
  const [applying, setApplying] = useState<string>();
  const [lastApplied, setLastApplied] = useState<string>();

  useEffect(() => {
    apiClient
      .getProfiles()
      .then(setProfiles)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unreachable'));
  }, []);

  const handleApply = useCallback(async (name: string) => {
    setApplying(name);
    setError(undefined);
    try {
      await apiClient.applyProfile(name);
      setLastApplied(name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Apply failed');
    } finally {
      setApplying(undefined);
    }
  }, []);

  return (
    <div className="panel">
      <div className="panel-title">Capability Profiles</div>
      {error && <div className="error-msg">{error}</div>}
      {!profiles && !error && <div className="loading">Loading…</div>}
      {profiles && profiles.length === 0 && <div className="empty">No profiles defined</div>}
      {profiles && profiles.length > 0 && (
        <ul className="event-list">
          {profiles.map((p) => (
            <li key={p.name} className="event-item profile-row">
              <div className="profile-info">
                <span className="event-type">{p.name}</span>
                {lastApplied === p.name && (
                  <span className="badge badge-ok" style={{ marginLeft: 8 }}>active</span>
                )}
                <div className="event-payload">{p.description}</div>
              </div>
              <button
                className="profile-apply"
                disabled={applying === p.name}
                onClick={() => handleApply(p.name)}
              >
                Apply
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
