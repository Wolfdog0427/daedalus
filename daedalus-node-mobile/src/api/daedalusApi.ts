/**
 * Daedalus API client for the mobile app.
 * Talks to the orchestrator at the configured URL.
 */
import Constants from 'expo-constants';

export type ChatRole = 'operator' | 'daedalus' | 'system';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

export interface SystemStatus {
  strategy: string;
  alignment: number;
  confidence: number;
  operatorBound: boolean;
  operatorName: string | null;
  trustPosture: string;
  trustScore: number;
  nodeCount: number;
  quarantinedCount: number;
  totalErrors: number;
  safeModeActive: boolean;
  freezeFrozen: boolean;
  governancePosture: string;
  lastUpdated: string;
}

function getBaseUrl(): string {
  const extra = Constants.expoConfig?.extra as { orchestratorUrl?: string } | undefined;
  return (extra?.orchestratorUrl ?? 'http://10.0.2.2:3001').replace(/\/+$/, '');
}

function getToken(): string {
  const extra = Constants.expoConfig?.extra as { daedalusToken?: string } | undefined;
  return extra?.daedalusToken ?? 'daedalus-dev-token';
}

function headers(): Record<string, string> {
  return { 'Content-Type': 'application/json', 'x-daedalus-token': getToken() };
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${getBaseUrl()}/daedalus${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${getBaseUrl()}/daedalus${path}`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${getBaseUrl()}/daedalus${path}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function sendChatMessage(content: string): Promise<{
  userMessage: ChatMessage;
  daedalusMessage: ChatMessage;
}> {
  return post('/chat', { content });
}

export async function fetchChatHistory(limit = 100): Promise<ChatMessage[]> {
  return get(`/chat/history?limit=${limit}`);
}

export async function clearChatHistory(): Promise<void> {
  await del('/chat/history');
}

export async function fetchChatWelcome(): Promise<ChatMessage> {
  return get('/chat/welcome');
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const [strategy, trust, governance, nodes] = await Promise.all([
    get<any>('/strategy').catch(() => null),
    get<any>('/operator/trust').catch(() => null),
    get<any>('/governance/posture').catch(() => null),
    get<any>('/mirror/nodes').catch(() => null),
  ]);

  const nodeList: any[] = Array.isArray(nodes) ? nodes : [];

  return {
    strategy: strategy?.strategy ?? 'unknown',
    alignment: strategy?.alignment ?? 0,
    confidence: strategy?.confidence ?? 0,
    operatorBound: !!trust?.boundOperatorId,
    operatorName: trust?.boundOperatorName ?? null,
    trustPosture: trust?.posture ?? 'unbound',
    trustScore: trust?.trustScore ?? 0,
    nodeCount: nodeList.length,
    quarantinedCount: nodeList.filter((n: any) => n.status === 'quarantined').length,
    totalErrors: nodeList.reduce((s: number, n: any) => s + (n.errorCount ?? 0), 0),
    safeModeActive: strategy?.safeMode?.active ?? false,
    freezeFrozen: trust?.freeze?.frozen ?? false,
    governancePosture: governance?.posture ?? 'OPEN',
    lastUpdated: new Date().toISOString(),
  };
}

export type ChangeProposalKind =
  | 'alignment_config' | 'governance_policy' | 'regulation_tuning'
  | 'posture_shift' | 'node_authority' | 'identity_update'
  | 'telemetry_config' | 'other';

export interface ApprovalReasonBreakdown {
  alignmentOK: boolean;
  confidenceOK: boolean;
  impactOK: boolean;
  invariantsOK: boolean;
  reversibleOK: boolean;
  safeModeOK: boolean;
  cooldownOK: boolean;
}

export interface ApprovalDecision {
  autoApprove: boolean;
  proposal: {
    id?: string;
    kind: ChangeProposalKind;
    description: string;
    proposedAt: number;
  };
  reasons: ApprovalReasonBreakdown;
  derivedImpact: 'low' | 'medium' | 'high';
  alignment: number;
  confidence: number;
  decidedAt: number;
}

export interface ApprovalGateConfig {
  alignmentThreshold: number;
  confidenceThreshold: number;
  cooldownMs: number;
  allowDuringSafeMode: boolean;
}

export interface ApprovalGateResponse {
  config: ApprovalGateConfig;
  recentDecisions: ApprovalDecision[];
}

export interface RollbackRegistrySnapshot {
  activeChanges: { id: string; description: string; status: string }[];
  recentRollbacks: { changeId: string; reason: string }[];
  acceptedCount: number;
  rolledBackCount: number;
}

export interface DaedalusProposal {
  id: string;
  kind: string;
  title: string;
  description: string;
  rationale: string;
  alignment: number;
  confidence: number;
  impact: 'low' | 'medium' | 'high';
  touchesInvariants: boolean;
  reversible: boolean;
  autoApprovable: boolean;
  payload: Record<string, unknown>;
  createdAt: number;
  status: 'pending' | 'approved' | 'denied' | 'expired' | 'auto_approved';
  resolvedAt?: number;
  effectBaseline?: number;
  effectAfter?: number;
}

export interface ProposalHistoryEntry {
  id: string;
  title: string;
  kind: string;
  status: 'approved' | 'denied' | 'auto_approved' | 'expired';
  alignment: number;
  confidence: number;
  impact: 'low' | 'medium' | 'high';
  effectBaseline: number | null;
  effectAfter: number | null;
  effectDelta: number | null;
  createdAt: number;
  resolvedAt: number;
}

export async function fetchApprovalGate(): Promise<ApprovalGateResponse> {
  return get('/approval-gate');
}

export async function submitChangeProposal(
  kind: ChangeProposalKind,
  description: string
): Promise<ApprovalDecision> {
  return post('/propose-change', { kind, description });
}

export async function fetchRollbackRegistry(): Promise<RollbackRegistrySnapshot> {
  return get('/rollback-registry');
}

export async function fetchPendingProposals(): Promise<DaedalusProposal[]> {
  return get('/proposals/pending');
}

export async function fetchProposalHistory(): Promise<ProposalHistoryEntry[]> {
  return get('/proposals/history');
}

export async function approveDaedalusProposal(id: string): Promise<DaedalusProposal> {
  return post(`/proposals/${id}/approve`, {});
}

export async function denyDaedalusProposal(id: string): Promise<DaedalusProposal> {
  return post(`/proposals/${id}/deny`, {});
}

export async function sendHeartbeat(nodeId: string): Promise<boolean> {
  try {
    const res = await fetch(`${getBaseUrl()}/daedalus/mirror/heartbeat`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ nodeId, timestamp: new Date().toISOString(), status: 'alive' }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
