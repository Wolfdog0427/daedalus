export type PostureProfileId = string;
export type IdentityAnchorId = string;
export type ContinuityEventId = string;

export interface PostureProfile {
  id: PostureProfileId;
  label: string;
  description?: string;
  comfort: 'low' | 'medium' | 'high';
  autonomy: 'low' | 'medium' | 'high';
  defenseMode: 'relaxed' | 'guarded' | 'locked';
}

export interface IdentityAnchor {
  id: IdentityAnchorId;
  label: string;
  kind: 'operator' | 'node' | 'environment';
  value: string;
}

export interface ContinuityEvent {
  id: ContinuityEventId;
  kind: string;
  at: number;
  payload?: Record<string, unknown>;
}

export interface NotificationPayload {
  level: 'info' | 'warn' | 'error';
  message: string;
  surface?: string;
  meta?: Record<string, unknown>;
}

export interface DaedalusState {
  postureProfile: PostureProfile | null;
  identityAnchors: IdentityAnchor[];
  continuityEvents: ContinuityEvent[];
}

export interface DaedalusContextValue {
  state: DaedalusState;
  posture: {
    setProfile: (id: PostureProfileId) => void;
  };
  identity: {
    setAnchor: (id: IdentityAnchorId, value: string) => void;
  };
  continuity: {
    markEvent: (kind: string, payload?: Record<string, unknown>) => void;
  };
  notify: {
    info: (message: string, meta?: Record<string, unknown>) => void;
    warn: (message: string, meta?: Record<string, unknown>) => void;
    error: (message: string, meta?: Record<string, unknown>) => void;
  };
}
