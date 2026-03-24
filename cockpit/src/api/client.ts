import type {
  HealthResponse,
  StateResponse,
  ContextResponse,
  NodesResponse,
  RiskResponse,
  TimelineResponse,
  GlowResponse,
  CapabilityItem,
  CapabilityProfile,
  NodeCapabilityState,
  NotificationItem,
} from './types';

const ORCHESTRATOR_BASE_URL =
  import.meta.env.VITE_ORCHESTRATOR_URL ?? 'http://localhost:4000';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${ORCHESTRATOR_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed with ${res.status}`);
  }
  return res.json();
}

async function post<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${ORCHESTRATOR_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed with ${res.status}`);
  }
  return res.json();
}

async function patch<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${ORCHESTRATOR_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`PATCH ${path} failed with ${res.status}`);
  }
  return res.json();
}

export const apiClient = {
  getHealth(): Promise<HealthResponse> {
    return get('/health');
  },
  getState(): Promise<StateResponse> {
    return get('/state');
  },
  getContext(): Promise<ContextResponse> {
    return get('/context');
  },
  getNodes(): Promise<NodesResponse> {
    return get('/nodes');
  },
  getRisk(): Promise<RiskResponse> {
    return get('/risk');
  },
  getTimeline(): Promise<TimelineResponse> {
    return get('/continuity/timeline');
  },
  getGlow(): Promise<GlowResponse> {
    return get('/glow');
  },
  getCapabilities(): Promise<CapabilityItem[]> {
    return get('/capabilities');
  },
  patchCapability(name: string, enabled: boolean): Promise<CapabilityItem> {
    return patch(`/capabilities/${encodeURIComponent(name)}`, { enabled });
  },
  getNotifications(): Promise<NotificationItem[]> {
    return get('/notifications');
  },
  getProfiles(): Promise<CapabilityProfile[]> {
    return get('/profiles');
  },
  applyProfile(name: string): Promise<CapabilityProfile> {
    return post(`/profiles/${encodeURIComponent(name)}/apply`, {});
  },
  listNodeCapabilities(): Promise<NodeCapabilityState[]> {
    return get('/nodes/capabilities');
  },
  getNodeCapabilities(nodeId: string): Promise<NodeCapabilityState> {
    return get(`/nodes/${encodeURIComponent(nodeId)}/capabilities`);
  },
  applyProfileToNode(nodeId: string, profileName: string): Promise<NodeCapabilityState> {
    return post(`/nodes/${encodeURIComponent(nodeId)}/profiles/${encodeURIComponent(profileName)}/apply`, {});
  },
  negotiateCapabilities(): Promise<Record<string, boolean>> {
    return post('/capabilities/negotiate', {});
  },
  sendEvent(event: any): Promise<{ accepted: boolean }> {
    return post('/events', event);
  },
  sendCommand(command: any): Promise<{ accepted: boolean }> {
    return post('/commands', command);
  },
};
