import React from 'react';
import { createInitialState, setPostureProfile, setIdentityAnchor, addContinuityEvent, dispatchNotification } from './engine';
import { DaedalusContextValue, DaedalusState } from './types';

export const DaedalusContext = React.createContext<DaedalusContextValue | null>(null);

export const DaedalusProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [state, setState] = React.useState<DaedalusState>(() => createInitialState());

  const posture = React.useMemo(
    () => ({
      setProfile: (id: string) => {
        setState(prev => setPostureProfile(prev, id));
      },
    }),
    []
  );

  const identity = React.useMemo(
    () => ({
      setAnchor: (id: string, value: string) => {
        setState(prev => setIdentityAnchor(prev, id, value));
      },
    }),
    []
  );

  const continuity = React.useMemo(
    () => ({
      markEvent: (kind: string, payload?: Record<string, unknown>) => {
        setState(prev => addContinuityEvent(prev, kind, payload));
      },
    }),
    []
  );

  const notify = React.useMemo(
    () => ({
      info: (message: string, meta?: Record<string, unknown>) =>
        dispatchNotification({ level: 'info', message, meta }),
      warn: (message: string, meta?: Record<string, unknown>) =>
        dispatchNotification({ level: 'warn', message, meta }),
      error: (message: string, meta?: Record<string, unknown>) =>
        dispatchNotification({ level: 'error', message, meta }),
    }),
    []
  );

  const value = React.useMemo<DaedalusContextValue>(
    () => ({
      state,
      posture,
      identity,
      continuity,
      notify,
    }),
    [state, posture, identity, continuity, notify]
  );

  return <DaedalusContext.Provider value={value}>{children}</DaedalusContext.Provider>;
};
