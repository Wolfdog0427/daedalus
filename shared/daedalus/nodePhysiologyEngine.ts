import {
  NodeId,
  NodeHealthSnapshot,
  NodeRiskTier,
  NodePhysiologyState,
  NodePosture,
  GlowProfile,
  ComfortFlag,
  NODE_PHYSIOLOGY_IDLE,
} from './nodeContracts';

export interface PhysiologySignals {
  readonly health: NodeHealthSnapshot;
  readonly riskTier: NodeRiskTier;
  readonly operatorAttention: number;
  readonly emotionalTrajectory: 'stable' | 'rising' | 'falling' | 'volatile';
}

export function derivePosture(
  health: NodeHealthSnapshot,
  riskTier: NodeRiskTier,
): NodePosture {
  if (health.degraded) return 'DEGRADED';
  if (riskTier === NodeRiskTier.QUARANTINED) return 'DEFENSIVE';
  if (riskTier === NodeRiskTier.HIGH) return 'ALERT';
  if (riskTier === NodeRiskTier.MEDIUM) return 'ALERT';
  if (!health.liveness) return 'DEGRADED';
  return 'CALM';
}

export function deriveGlowProfile(
  posture: NodePosture,
  health: NodeHealthSnapshot,
): GlowProfile {
  switch (posture) {
    case 'CALM':
      return Object.freeze({
        intensity: 0.6,
        colorBand: '#4da3ff',
        motionPattern: 'breathe' as const,
      });
    case 'ALERT':
      return Object.freeze({
        intensity: 0.8,
        colorBand: '#ffd86b',
        motionPattern: 'pulse' as const,
      });
    case 'DEFENSIVE':
      return Object.freeze({
        intensity: 0.9,
        colorBand: '#ff4d4d',
        motionPattern: 'flicker' as const,
      });
    case 'DEGRADED':
      return Object.freeze({
        intensity: health.liveness ? 0.3 : 0.1,
        colorBand: '#6b6b6b',
        motionPattern: 'steady' as const,
      });
  }
}

export function deriveComfortFlags(
  health: NodeHealthSnapshot,
  riskTier: NodeRiskTier,
): ComfortFlag[] {
  const flags: ComfortFlag[] = [];
  if (health.batteryBand === 'LOW' || health.batteryBand === 'CRITICAL') {
    flags.push('LOW_BATTERY');
  }
  if (health.connectivityBand === 'WEAK' || health.connectivityBand === 'OFFLINE') {
    flags.push('UNSTABLE_NETWORK');
  }
  if (riskTier === NodeRiskTier.HIGH || riskTier === NodeRiskTier.QUARANTINED) {
    flags.push('HIGH_RISK_CONTEXT');
  }
  if (riskTier === NodeRiskTier.QUARANTINED) {
    flags.push('QUARANTINE_RISK');
  }
  return flags;
}

export function deriveAttentionWeight(
  operatorAttention: number,
  emotionalTrajectory: PhysiologySignals['emotionalTrajectory'],
): number {
  let weight = Math.max(0, Math.min(1, operatorAttention));
  if (emotionalTrajectory === 'volatile') weight = Math.min(1, weight + 0.2);
  if (emotionalTrajectory === 'falling') weight = Math.max(0, weight - 0.1);
  return Math.round(weight * 100) / 100;
}

export function computePhysiologyState(
  nodeId: NodeId,
  signals: PhysiologySignals,
): NodePhysiologyState {
  const posture = derivePosture(signals.health, signals.riskTier);
  const glowProfile = deriveGlowProfile(posture, signals.health);
  const comfortFlags = deriveComfortFlags(signals.health, signals.riskTier);
  const attentionWeight = deriveAttentionWeight(
    signals.operatorAttention,
    signals.emotionalTrajectory,
  );

  return Object.freeze({
    nodeId,
    posture,
    glowProfile,
    attentionWeight,
    comfortFlags,
    timestamp: Date.now(),
  });
}

export function computeIdlePhysiology(nodeId: NodeId): NodePhysiologyState {
  return Object.freeze({ ...NODE_PHYSIOLOGY_IDLE, nodeId, timestamp: Date.now() });
}
