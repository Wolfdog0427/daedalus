import type {
  OrchestratorSnapshot,
  CapabilityTrace,
  NegotiationPreview,
  NegotiationApplyResult,
  NegotiationInput,
  PostureSnapshot,
  GovernanceOverride,
  ContinuityDrift,
  BeingPresenceDetail,
} from "../shared/daedalus/contracts";

const basePath = import.meta.env.VITE_DAEDALUS_API_BASE || "/daedalus";

const TOKEN = import.meta.env.VITE_DAEDALUS_TOKEN ?? "daedalus-dev-token";

function authHeaders(): Record<string, string> {
  return { "Content-Type": "application/json", "x-daedalus-token": TOKEN };
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Daedalus API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function handleVoid(res: Response): Promise<void> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Daedalus API error ${res.status}: ${text}`);
  }
}

export async function fetchSnapshot(): Promise<OrchestratorSnapshot> {
  const res = await fetch(`${basePath}/snapshot`, { headers: authHeaders() });
  return handleJson<OrchestratorSnapshot>(res);
}

export async function fetchCapabilityTrace(
  nodeId: string,
  capabilityName: string,
): Promise<CapabilityTrace> {
  const params = new URLSearchParams({ nodeId, capabilityName });
  const res = await fetch(`${basePath}/capabilities/trace?${params.toString()}`, {
    headers: authHeaders(),
  });
  return handleJson<CapabilityTrace>(res);
}

export async function previewNegotiation(
  input: NegotiationInput,
): Promise<NegotiationPreview> {
  const res = await fetch(`${basePath}/negotiations/preview`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationPreview>(res);
}

export async function applyNegotiation(
  input: NegotiationInput,
): Promise<NegotiationApplyResult> {
  const res = await fetch(`${basePath}/negotiations/apply`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationApplyResult>(res);
}

export async function fetchPosture(): Promise<PostureSnapshot> {
  const res = await fetch(`${basePath}/governance/posture`, { headers: authHeaders() });
  return handleJson<PostureSnapshot>(res);
}

export async function fetchOverrides(): Promise<GovernanceOverride[]> {
  const res = await fetch(`${basePath}/governance/overrides`, { headers: authHeaders() });
  return handleJson<GovernanceOverride[]>(res);
}

export async function fetchDrifts(): Promise<ContinuityDrift[]> {
  const res = await fetch(`${basePath}/governance/drifts`, { headers: authHeaders() });
  return handleJson<ContinuityDrift[]>(res);
}

export async function fetchBeingPresences(): Promise<BeingPresenceDetail[]> {
  const res = await fetch(`${basePath}/beings/presence`, { headers: authHeaders() });
  return handleJson<BeingPresenceDetail[]>(res);
}

export async function updateBeingPresence(
  beingId: string,
  patch: Partial<BeingPresenceDetail>,
): Promise<BeingPresenceDetail> {
  const res = await fetch(`${basePath}/beings/${beingId}/presence`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<BeingPresenceDetail>(res);
}

// ── Cockpit (sensory cortex) ──────────────────────────────────────

export interface CockpitNodeView {
  id: string;
  name: string;
  status: string;
  risk: string;
  phase: string;
  kind: string;
  glow: string;
  glowIntensity: number;
  posture: string;
  attention: { level: string; targetNodeId?: string };
  continuity: string;
  capabilities: string[];
  heartbeatCount: number;
  lastHeartbeatAt: string | null;
  errorCount: number;
}

export interface CockpitSummary {
  totalNodes: number;
  byStatus: Record<string, number>;
  byPosture: Record<string, number>;
  byRisk: Record<string, number>;
  totalErrors: number;
  posture?: string;
  postureReason?: string;
  urgency?: "calm" | "attentive" | "elevated" | "critical";
  recommendedActions?: string[];
  activeDriftCount?: number;
  activeOverrideCount?: number;
}

export interface Incident {
  id: string;
  title: string;
  notes: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "open" | "investigating" | "mitigated" | "resolved";
  openedAt: string;
  closedAt: string | null;
  updatedAt: string;
}

export interface ActionEntry {
  id: number;
  kind: string;
  timestamp: string;
  payload: any;
  undone: boolean;
  undoable: boolean;
}

export async function fetchCockpitNodes(): Promise<CockpitNodeView[]> {
  const res = await fetch(`${basePath}/cockpit/nodes`, { headers: authHeaders() });
  return handleJson<CockpitNodeView[]>(res);
}

export async function fetchCockpitSummary(): Promise<CockpitSummary> {
  const res = await fetch(`${basePath}/cockpit/summary`, { headers: authHeaders() });
  return handleJson<CockpitSummary>(res);
}

export async function createOverride(input: {
  createdBy: { id: string; role: string; label: string };
  reason: string;
  scope: string;
  targetId?: string;
  effect: string;
}): Promise<GovernanceOverride> {
  const res = await fetch(`${basePath}/governance/overrides`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<GovernanceOverride>(res);
}

export async function removeOverride(id: string): Promise<void> {
  const res = await fetch(`${basePath}/governance/overrides/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function clearOverrides(): Promise<void> {
  const res = await fetch(`${basePath}/governance/overrides`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function castVote(input: {
  being: { id: string; role: string; label: string };
  vote: string;
  weight: number;
}): Promise<any> {
  const res = await fetch(`${basePath}/governance/votes`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<any>(res);
}

export async function fetchVotes(): Promise<any[]> {
  const res = await fetch(`${basePath}/governance/votes`, { headers: authHeaders() });
  return handleJson<any[]>(res);
}

export async function clearVotes(): Promise<void> {
  const res = await fetch(`${basePath}/governance/votes`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function clearDrifts(): Promise<void> {
  const res = await fetch(`${basePath}/governance/drifts`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function fetchConstitution(): Promise<any> {
  const res = await fetch(`${basePath}/constitution`, { headers: authHeaders() });
  return handleJson<any>(res);
}

// ── Event History ──────────────────────────────────────────────────

export async function fetchEventHistory(limit = 100, type?: string): Promise<any[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (type) params.set("type", type);
  const res = await fetch(`${basePath}/events/history?${params.toString()}`, { headers: authHeaders() });
  return handleJson<any[]>(res);
}

// ── Incidents ──────────────────────────────────────────────────────

export async function fetchIncidents(status?: string): Promise<Incident[]> {
  const params = status ? `?status=${status}` : "";
  const res = await fetch(`${basePath}/incidents${params}`, { headers: authHeaders() });
  return handleJson<Incident[]>(res);
}

export async function openIncident(input: { title: string; notes?: string; severity: string }): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<Incident>(res);
}

export async function updateIncident(id: string, patch: Partial<Incident>): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<Incident>(res);
}

export async function resolveIncident(id: string): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents/${id}/resolve`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<Incident>(res);
}

// ── Action Log & Undo ──────────────────────────────────────────────

export async function fetchActions(limit = 50): Promise<ActionEntry[]> {
  const res = await fetch(`${basePath}/actions?limit=${limit}`, { headers: authHeaders() });
  return handleJson<ActionEntry[]>(res);
}

export async function undoAction(actionId: number): Promise<{ success: boolean }> {
  const res = await fetch(`${basePath}/actions/${actionId}/undo`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<{ success: boolean }>(res);
}
