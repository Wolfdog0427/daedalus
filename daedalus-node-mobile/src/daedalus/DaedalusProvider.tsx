import React from 'react';
import { createInitialState, setPostureProfile, setIdentityAnchor, addContinuityEvent, dispatchNotification } from './engine';
import { DaedalusContextValue, DaedalusState } from './types';
import { IDENTITY } from '../config/identity';
import {
  fetchSystemStatus,
  sendHeartbeat,
  fetchChatHistory,
  fetchChatWelcome,
  sendChatMessage,
  clearChatHistory as apiClearChat,
  type SystemStatus,
  type ChatMessage,
} from '../api/daedalusApi';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface DaedalusContextExt extends DaedalusContextValue {
  connection: ConnectionStatus;
  systemStatus: SystemStatus | null;
  chatMessages: ChatMessage[];
  chatSending: boolean;
  sendChat: (content: string) => Promise<void>;
  clearChat: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

export const DaedalusContext = React.createContext<DaedalusContextExt | null>(null);

const HEARTBEAT_MS = 15_000;
const STATUS_POLL_MS = 10_000;

export const DaedalusProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [state, setState] = React.useState<DaedalusState>(() => createInitialState());
  const [connection, setConnection] = React.useState<ConnectionStatus>('disconnected');
  const [systemStatus, setSystemStatus] = React.useState<SystemStatus | null>(null);
  const [chatMessages, setChatMessages] = React.useState<ChatMessage[]>([]);
  const [chatSending, setChatSending] = React.useState(false);
  const [chatInitialized, setChatInitialized] = React.useState(false);

  React.useEffect(() => {
    let alive = true;

    async function heartbeatLoop() {
      while (alive) {
        setConnection(prev => prev === 'disconnected' ? 'connecting' : prev);
        const ok = await sendHeartbeat(IDENTITY.nodeId);
        if (!alive) break;
        setConnection(ok ? 'connected' : 'error');
        await new Promise(r => setTimeout(r, HEARTBEAT_MS));
      }
    }

    async function statusLoop() {
      await new Promise(r => setTimeout(r, 2000));
      while (alive) {
        try {
          const s = await fetchSystemStatus();
          if (alive) setSystemStatus(s);
        } catch { /* silent */ }
        await new Promise(r => setTimeout(r, STATUS_POLL_MS));
      }
    }

    heartbeatLoop();
    statusLoop();

    return () => { alive = false; };
  }, []);

  React.useEffect(() => {
    if (chatInitialized) return;
    let cancelled = false;

    (async () => {
      try {
        const history = await fetchChatHistory();
        if (cancelled) return;
        if (history.length > 0) {
          setChatMessages(history);
        } else {
          const welcome = await fetchChatWelcome();
          if (!cancelled) setChatMessages([welcome]);
        }
      } catch {
        try {
          const welcome = await fetchChatWelcome();
          if (!cancelled) setChatMessages([welcome]);
        } catch { /* silent */ }
      }
      if (!cancelled) setChatInitialized(true);
    })();

    return () => { cancelled = true; };
  }, [chatInitialized]);

  const sendChat = React.useCallback(async (content: string) => {
    if (!content.trim() || chatSending) return;

    const optimistic: ChatMessage = {
      id: `opt-${Date.now()}`,
      role: 'operator',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, optimistic]);
    setChatSending(true);

    try {
      const { userMessage, daedalusMessage } = await sendChatMessage(content.trim());
      setChatMessages(prev => {
        const without = prev.filter(m => m.id !== optimistic.id);
        return [...without, userMessage, daedalusMessage];
      });
    } catch {
      setChatMessages(prev => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'system', content: 'Failed to send message.', timestamp: new Date().toISOString() },
      ]);
    } finally {
      setChatSending(false);
    }
  }, [chatSending]);

  const clearChat = React.useCallback(async () => {
    try {
      await apiClearChat();
      setChatMessages([]);
      setChatInitialized(false);
    } catch { /* ignore */ }
  }, []);

  const refreshStatus = React.useCallback(async () => {
    try {
      const s = await fetchSystemStatus();
      setSystemStatus(s);
    } catch { /* ignore */ }
  }, []);

  const posture = React.useMemo(() => ({
    setProfile: (id: string) => setState(prev => setPostureProfile(prev, id)),
  }), []);

  const identity = React.useMemo(() => ({
    setAnchor: (id: string, value: string) => setState(prev => setIdentityAnchor(prev, id, value)),
  }), []);

  const continuity = React.useMemo(() => ({
    markEvent: (kind: string, payload?: Record<string, unknown>) => setState(prev => addContinuityEvent(prev, kind, payload)),
  }), []);

  const notify = React.useMemo(() => ({
    info: (msg: string, meta?: Record<string, unknown>) => dispatchNotification({ level: 'info', message: msg, meta }),
    warn: (msg: string, meta?: Record<string, unknown>) => dispatchNotification({ level: 'warn', message: msg, meta }),
    error: (msg: string, meta?: Record<string, unknown>) => dispatchNotification({ level: 'error', message: msg, meta }),
  }), []);

  const value = React.useMemo<DaedalusContextExt>(() => ({
    state,
    posture,
    identity,
    continuity,
    notify,
    connection,
    systemStatus,
    chatMessages,
    chatSending,
    sendChat,
    clearChat,
    refreshStatus,
  }), [state, posture, identity, continuity, notify, connection, systemStatus, chatMessages, chatSending, sendChat, clearChat, refreshStatus]);

  return <DaedalusContext.Provider value={value}>{children}</DaedalusContext.Provider>;
};
