import { useState, type FormEvent } from 'react';
import { apiClient } from '../api/client';

interface CommandEntry {
  type: string;
  message: string;
  accepted: boolean;
  timestamp: string;
}

export function EchoCommandPanel() {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<CommandEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  // Hook: add more command types and a selector later

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message) return;

    setLoading(true);
    setError(undefined);

    try {
      const res = await apiClient.sendCommand({
        type: 'echo',
        payload: { message },
      });
      setHistory((prev) => [
        {
          type: 'echo',
          message,
          accepted: res.accepted,
          timestamp: new Date().toISOString(),
        },
        ...prev,
      ]);
      setInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Command failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">Commands</div>
      <form className="command-form" onSubmit={handleSubmit}>
        <input
          className="command-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="echo message…"
          disabled={loading}
        />
        <button
          className="command-btn"
          type="submit"
          disabled={loading || !input.trim()}
        >
          {loading ? '…' : 'Send'}
        </button>
      </form>
      {error && <div className="error-msg">{error}</div>}
      {history.length > 0 && (
        <ul className="echo-history">
          {history.map((entry, i) => (
            <li key={`${entry.timestamp}-${i}`} className="echo-entry">
              <span>↩ {entry.message}</span>{' '}
              <span style={{ color: 'var(--text-dim)' }}>
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
