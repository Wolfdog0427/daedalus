export interface HealthResponse {
  status: string;
  version: string;
  posture: {
    mode: string;
    lastChangedAt: string | null;
    reason?: string;
  };
  risk: string;
  glow: string;
}

export interface StateResponse {
  state: any;
  presence: any;
  continuity: any;
  posture: any;
  risk: {
    tier: string;
    assessedAt: string;
    factors: string[];
  };
  verification: {
    requirement: string;
    lastEvent: {
      timestamp: string;
      method: string;
      actor: string;
    } | null;
  };
  glow: {
    hue: string;
    intensity: number;
    label: string;
  };
}

export interface ContextResponse {
  system: {
    env: string;
    version: string;
    startedAt: string;
  };
  operator: {
    id: string | null;
    label: string | null;
    roles: string[];
  };
}

export interface NodesResponse {
  nodes: Record<string, {
    id: string;
    capabilities: string[];
    lastHeartbeat: string;
    registeredAt: string;
    meta?: Record<string, any>;
  }>;
  count: number;
}

export interface RiskResponse {
  risk: {
    tier: string;
    assessedAt: string;
    factors: string[];
  };
  verification: {
    requirement: string;
    lastEvent: {
      timestamp: string;
      method: string;
      actor: string;
    } | null;
  };
}

export interface TimelineEntry {
  timestamp: string;
  type: string;
  threadId?: string;
  summary?: string;
  postureAtTime?: string;
}

export interface TimelineResponse {
  entries: TimelineEntry[];
  threadIds: string[];
}

export interface GlowResponse {
  hue: string;
  intensity: number;
  label: string;
}

export interface CapabilityItem {
  name: string;
  description: string;
  enabled: boolean;
}

export interface NotificationItem {
  id: string;
  type: string;
  payload: any;
  timestamp: string;
}

export interface CapabilityProfile {
  name: string;
  description: string;
  capabilities: Record<string, boolean>;
}

export interface NodeCapabilityState {
  nodeId: string;
  capabilities: Record<string, boolean>;
}
