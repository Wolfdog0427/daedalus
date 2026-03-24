import type {
  GlowState,
  GlowLevel,
  DaedalusPosture,
  AttentionState,
  ContinuityState,
} from "../../shared/daedalus/contracts";
import type { NodeAgentTransport } from "./NodeAgent.transport";

export interface AgentExpressiveState {
  glow: GlowState;
  posture: DaedalusPosture;
  attention: AttentionState;
  continuity: ContinuityState;
}

export const IDLE_AGENT_EXPRESSIVE: AgentExpressiveState = Object.freeze({
  glow: Object.freeze({ level: "medium" as GlowLevel, intensity: 0.5 }),
  posture: "observer" as DaedalusPosture,
  attention: Object.freeze({ level: "aware" as const }),
  continuity: Object.freeze({ streak: 0, lastCheckIn: "", healthy: false }),
});

export function createExpressiveManager(
  nodeId: string,
  transport: NodeAgentTransport,
) {
  let state: AgentExpressiveState = { ...IDLE_AGENT_EXPRESSIVE };
  let syncTimer: ReturnType<typeof setInterval> | null = null;
  const listeners = new Set<(state: AgentExpressiveState) => void>();

  function emit() {
    for (const fn of listeners) fn(state);
  }

  return {
    getState(): AgentExpressiveState { return state; },

    setGlow(glow: GlowState) {
      state = { ...state, glow };
      emit();
    },

    setPosture(posture: DaedalusPosture) {
      state = { ...state, posture };
      emit();
    },

    setAttention(attention: AttentionState) {
      state = { ...state, attention };
      emit();
    },

    setContinuity(continuity: ContinuityState) {
      state = { ...state, continuity };
      emit();
    },

    async sync(): Promise<void> {
      await transport.post("/daedalus/mirror/expressive", {
        nodeId,
        expressive: state,
        timestamp: new Date().toISOString(),
      });
    },

    startPeriodicSync(intervalMs: number) {
      if (syncTimer) return;
      syncTimer = setInterval(() => {
        void this.sync();
      }, intervalMs);
    },

    stopPeriodicSync() {
      if (syncTimer) {
        clearInterval(syncTimer);
        syncTimer = null;
      }
    },

    onStateChange(handler: (s: AgentExpressiveState) => void): () => void {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },
  };
}

export type ExpressiveManager = ReturnType<typeof createExpressiveManager>;
