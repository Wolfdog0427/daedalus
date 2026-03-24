import type { NodeAgentConfig } from "./NodeAgent.config";
import type { NodeAgentTransport, TransportResponse } from "./NodeAgent.transport";

export type AgentPhase = "idle" | "joining" | "active" | "degraded" | "disconnected" | "error";

export interface LifecycleState {
  phase: AgentPhase;
  joinedAt: string | null;
  lastHeartbeat: string | null;
  heartbeatCount: number;
  errorCount: number;
  lastError: string | null;
  reconnectAttempts: number;
}

export const IDLE_LIFECYCLE_STATE: LifecycleState = Object.freeze({
  phase: "idle" as AgentPhase,
  joinedAt: null,
  lastHeartbeat: null,
  heartbeatCount: 0,
  errorCount: 0,
  lastError: null,
  reconnectAttempts: 0,
});

const nowIso = () => new Date().toISOString();

export function createLifecycleManager(
  config: NodeAgentConfig,
  transport: NodeAgentTransport,
) {
  let state: LifecycleState = { ...IDLE_LIFECYCLE_STATE };
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  const listeners = new Set<(state: LifecycleState) => void>();

  function emit() {
    for (const fn of listeners) fn(state);
  }

  function setPhase(phase: AgentPhase) {
    state = { ...state, phase };
    emit();
  }

  async function join(): Promise<boolean> {
    setPhase("joining");
    const res = await transport.post("/daedalus/mirror/join", {
      nodeId: config.nodeId,
      name: config.nodeName,
      profile: {
        id: config.nodeId,
        name: config.nodeName,
        kind: config.kind,
        model: config.model,
        os: config.os,
        osVersion: config.osVersion,
        operatorId: config.operatorId,
      },
      capabilities: config.capabilities,
      expressive: {
        glow: { level: "medium", intensity: 0.5 },
        posture: "observer",
        attention: { level: "aware" },
        continuity: { streak: 0, lastCheckIn: nowIso(), healthy: true },
      },
    });

    if (res.ok) {
      state = { ...state, phase: "active", joinedAt: nowIso(), reconnectAttempts: 0 };
      emit();
      return true;
    }

    state = {
      ...state,
      phase: "error",
      errorCount: state.errorCount + 1,
      lastError: res.error ?? "Join failed",
    };
    emit();
    return false;
  }

  async function sendHeartbeat(): Promise<void> {
    const res = await transport.post("/daedalus/mirror/heartbeat", {
      nodeId: config.nodeId,
      timestamp: nowIso(),
      status: state.phase === "degraded" ? "degraded" : "alive",
    });

    if (res.ok) {
      state = {
        ...state,
        lastHeartbeat: nowIso(),
        heartbeatCount: state.heartbeatCount + 1,
      };
      if (state.phase === "disconnected") {
        state = { ...state, phase: "active", reconnectAttempts: 0 };
      }
    } else {
      state = {
        ...state,
        errorCount: state.errorCount + 1,
        lastError: res.error ?? "Heartbeat failed",
      };
      if (state.phase === "active") {
        state = { ...state, phase: "disconnected", reconnectAttempts: state.reconnectAttempts + 1 };
      }
    }
    emit();
  }

  function startHeartbeat() {
    if (heartbeatTimer) return;
    heartbeatTimer = setInterval(() => {
      void sendHeartbeat();
    }, config.heartbeatIntervalMs);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  return {
    getState(): LifecycleState { return state; },
    join,
    sendHeartbeat,
    startHeartbeat,
    stopHeartbeat,
    setPhase,
    onStateChange(handler: (s: LifecycleState) => void): () => void {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },
  };
}

export type LifecycleManager = ReturnType<typeof createLifecycleManager>;
