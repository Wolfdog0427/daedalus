import {
  derivePosture,
  deriveGlowProfile,
  deriveComfortFlags,
  deriveAttentionWeight,
  computePhysiologyState,
  computeIdlePhysiology,
  PhysiologySignals,
} from '../../shared/daedalus/nodePhysiologyEngine';
import {
  NodeRiskTier,
  NodeHealthSnapshot,
  NODE_HEALTH_IDLE,
} from '../../shared/daedalus/nodeContracts';

function mkHealth(overrides: Partial<NodeHealthSnapshot> = {}): NodeHealthSnapshot {
  return {
    ...NODE_HEALTH_IDLE,
    nodeId: 'n1',
    liveness: true,
    batteryBand: 'HIGH',
    connectivityBand: 'STRONG',
    degraded: false,
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('derivePosture', () => {
  test('CALM when healthy and low risk', () => {
    expect(derivePosture(mkHealth(), NodeRiskTier.LOW)).toBe('CALM');
  });

  test('DEGRADED when degraded', () => {
    expect(derivePosture(mkHealth({ degraded: true }), NodeRiskTier.LOW)).toBe('DEGRADED');
  });

  test('DEFENSIVE when quarantined', () => {
    expect(derivePosture(mkHealth(), NodeRiskTier.QUARANTINED)).toBe('DEFENSIVE');
  });

  test('ALERT when high risk', () => {
    expect(derivePosture(mkHealth(), NodeRiskTier.HIGH)).toBe('ALERT');
  });

  test('ALERT when medium risk', () => {
    expect(derivePosture(mkHealth(), NodeRiskTier.MEDIUM)).toBe('ALERT');
  });

  test('DEGRADED when not live', () => {
    expect(derivePosture(mkHealth({ liveness: false }), NodeRiskTier.LOW)).toBe('DEGRADED');
  });
});

describe('deriveGlowProfile', () => {
  test('CALM → breathe pattern, blue band', () => {
    const glow = deriveGlowProfile('CALM', mkHealth());
    expect(glow.motionPattern).toBe('breathe');
    expect(glow.intensity).toBeCloseTo(0.6);
  });

  test('ALERT → pulse pattern', () => {
    const glow = deriveGlowProfile('ALERT', mkHealth());
    expect(glow.motionPattern).toBe('pulse');
    expect(glow.intensity).toBeCloseTo(0.8);
  });

  test('DEFENSIVE → flicker pattern', () => {
    const glow = deriveGlowProfile('DEFENSIVE', mkHealth());
    expect(glow.motionPattern).toBe('flicker');
  });

  test('DEGRADED offline → low intensity', () => {
    const glow = deriveGlowProfile('DEGRADED', mkHealth({ liveness: false }));
    expect(glow.intensity).toBeCloseTo(0.1);
    expect(glow.motionPattern).toBe('steady');
  });

  test('glow is frozen', () => {
    expect(Object.isFrozen(deriveGlowProfile('CALM', mkHealth()))).toBe(true);
  });
});

describe('deriveComfortFlags', () => {
  test('empty when healthy', () => {
    expect(deriveComfortFlags(mkHealth(), NodeRiskTier.LOW)).toEqual([]);
  });

  test('LOW_BATTERY when battery low', () => {
    const flags = deriveComfortFlags(mkHealth({ batteryBand: 'LOW' }), NodeRiskTier.LOW);
    expect(flags).toContain('LOW_BATTERY');
  });

  test('UNSTABLE_NETWORK when weak', () => {
    const flags = deriveComfortFlags(mkHealth({ connectivityBand: 'WEAK' }), NodeRiskTier.LOW);
    expect(flags).toContain('UNSTABLE_NETWORK');
  });

  test('HIGH_RISK_CONTEXT when high risk', () => {
    const flags = deriveComfortFlags(mkHealth(), NodeRiskTier.HIGH);
    expect(flags).toContain('HIGH_RISK_CONTEXT');
  });

  test('QUARANTINE_RISK when quarantined', () => {
    const flags = deriveComfortFlags(mkHealth(), NodeRiskTier.QUARANTINED);
    expect(flags).toContain('QUARANTINE_RISK');
    expect(flags).toContain('HIGH_RISK_CONTEXT');
  });
});

describe('deriveAttentionWeight', () => {
  test('clamps to 0-1', () => {
    expect(deriveAttentionWeight(1.5, 'stable')).toBeLessThanOrEqual(1);
    expect(deriveAttentionWeight(-0.5, 'stable')).toBeGreaterThanOrEqual(0);
  });

  test('volatile increases weight', () => {
    expect(deriveAttentionWeight(0.5, 'volatile')).toBeGreaterThan(0.5);
  });

  test('falling decreases weight', () => {
    expect(deriveAttentionWeight(0.5, 'falling')).toBeLessThan(0.5);
  });
});

describe('computePhysiologyState', () => {
  test('produces a frozen state', () => {
    const signals: PhysiologySignals = {
      health: mkHealth(),
      riskTier: NodeRiskTier.LOW,
      operatorAttention: 0.6,
      emotionalTrajectory: 'stable',
    };
    const state = computePhysiologyState('n1', signals);
    expect(state.nodeId).toBe('n1');
    expect(state.posture).toBe('CALM');
    expect(Object.isFrozen(state)).toBe(true);
  });
});

describe('computeIdlePhysiology', () => {
  test('idle has correct nodeId', () => {
    const idle = computeIdlePhysiology('x');
    expect(idle.nodeId).toBe('x');
    expect(idle.posture).toBe('CALM');
  });
});
