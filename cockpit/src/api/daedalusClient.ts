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

const basePath = "/daedalus";

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Daedalus API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchSnapshot(): Promise<OrchestratorSnapshot> {
  const res = await fetch(`${basePath}/snapshot`);
  return handleJson<OrchestratorSnapshot>(res);
}

export async function fetchCapabilityTrace(
  nodeId: string,
  capabilityName: string,
): Promise<CapabilityTrace> {
  const params = new URLSearchParams({ nodeId, capabilityName });
  const res = await fetch(`${basePath}/capabilities/trace?${params.toString()}`);
  return handleJson<CapabilityTrace>(res);
}

export async function previewNegotiation(
  input: NegotiationInput,
): Promise<NegotiationPreview> {
  const res = await fetch(`${basePath}/negotiations/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationPreview>(res);
}

export async function applyNegotiation(
  input: NegotiationInput,
): Promise<NegotiationApplyResult> {
  const res = await fetch(`${basePath}/negotiations/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationApplyResult>(res);
}

export async function fetchPosture(): Promise<PostureSnapshot> {
  const res = await fetch(`${basePath}/governance/posture`);
  return handleJson<PostureSnapshot>(res);
}

export async function fetchOverrides(): Promise<GovernanceOverride[]> {
  const res = await fetch(`${basePath}/governance/overrides`);
  return handleJson<GovernanceOverride[]>(res);
}

export async function fetchDrifts(): Promise<ContinuityDrift[]> {
  const res = await fetch(`${basePath}/governance/drifts`);
  return handleJson<ContinuityDrift[]>(res);
}

export async function fetchBeingPresences(): Promise<BeingPresenceDetail[]> {
  const res = await fetch(`${basePath}/beings/presence`);
  return handleJson<BeingPresenceDetail[]>(res);
}

export async function updateBeingPresence(
  beingId: string,
  patch: Partial<BeingPresenceDetail>,
): Promise<BeingPresenceDetail> {
  const res = await fetch(`${basePath}/beings/${beingId}/presence`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return handleJson<BeingPresenceDetail>(res);
}
