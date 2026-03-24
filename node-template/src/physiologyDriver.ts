import type { NodeId, NodeHealthSnapshot, NodePhysiologyState, NodeRiskTier } from '../../shared/daedalus/nodeContracts';
import {
  computePhysiologyState,
  computeIdlePhysiology,
  PhysiologySignals,
} from '../../shared/daedalus/nodePhysiologyEngine';
import type { NodeTransport } from './transport';
import type { ContinuitySignals } from './contracts';
import { NODE_HEALTH_IDLE, NodeRiskTier as RT } from '../../shared/daedalus/nodeContracts';

export interface PhysiologyDriverConfig {
  readonly nodeId: NodeId;
  readonly transport: NodeTransport;
}

export function createPhysiologyDriver(config: PhysiologyDriverConfig) {
  let currentHealth: NodeHealthSnapshot = { ...NODE_HEALTH_IDLE, nodeId: config.nodeId };
  let currentSignals: ContinuitySignals = {
    riskTier: RT.LOW,
    operatorAttention: 0.5,
    emotionalTrajectory: 'stable',
  };
  let currentState: NodePhysiologyState = computeIdlePhysiology(config.nodeId);
  const listeners = new Set<(state: NodePhysiologyState) => void>();

  function recompute() {
    const signals: PhysiologySignals = {
      health: currentHealth,
      riskTier: currentSignals.riskTier,
      operatorAttention: currentSignals.operatorAttention,
      emotionalTrajectory: currentSignals.emotionalTrajectory,
    };
    const next = computePhysiologyState(config.nodeId, signals);
    currentState = next;
    for (const fn of listeners) fn(next);
    config.transport.sendPhysiology(next).catch(() => {});
  }

  return {
    updateHealth(health: NodeHealthSnapshot) {
      currentHealth = health;
      recompute();
    },

    updateContinuitySignals(signals: ContinuitySignals) {
      currentSignals = signals;
      recompute();
    },

    getCurrentState(): NodePhysiologyState {
      return currentState;
    },

    onPhysiologyChange(handler: (state: NodePhysiologyState) => void): () => void {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },
  };
}

export type PhysiologyDriver = ReturnType<typeof createPhysiologyDriver>;
