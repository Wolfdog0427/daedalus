import { createPhysiologyDriver } from '../src/physiologyDriver';
import type { NodeTransport } from '../src/transport';
import {
  NodeRiskTier,
  NodeHealthSnapshot,
  NODE_HEALTH_IDLE,
} from '../../shared/daedalus/nodeContracts';

function mockTransport(): NodeTransport {
  return {
    sendJoinProposal: jest.fn().mockResolvedValue({}),
    sendHeartbeat: jest.fn().mockResolvedValue(undefined),
    sendPhysiology: jest.fn().mockResolvedValue(undefined),
  };
}

function mkHealth(overrides: Partial<NodeHealthSnapshot> = {}): NodeHealthSnapshot {
  return {
    ...NODE_HEALTH_IDLE,
    nodeId: 'n-test',
    liveness: true,
    batteryBand: 'HIGH',
    connectivityBand: 'STRONG',
    degraded: false,
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('createPhysiologyDriver', () => {
  test('starts with idle physiology', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });
    const state = driver.getCurrentState();
    expect(state.nodeId).toBe('n-test');
    expect(state.posture).toBe('CALM');
  });

  test('CALM posture for healthy + low risk', () => {
    const transport = mockTransport();
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport });

    driver.updateHealth(mkHealth());
    driver.updateContinuitySignals({
      riskTier: NodeRiskTier.LOW,
      operatorAttention: 0.5,
      emotionalTrajectory: 'stable',
    });

    expect(driver.getCurrentState().posture).toBe('CALM');
    expect(transport.sendPhysiology).toHaveBeenCalled();
  });

  test('ALERT posture for high risk', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth());
    driver.updateContinuitySignals({
      riskTier: NodeRiskTier.HIGH,
      operatorAttention: 0.5,
      emotionalTrajectory: 'stable',
    });

    expect(driver.getCurrentState().posture).toBe('ALERT');
  });

  test('DEFENSIVE posture for quarantined risk', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth());
    driver.updateContinuitySignals({
      riskTier: NodeRiskTier.QUARANTINED,
      operatorAttention: 0.5,
      emotionalTrajectory: 'stable',
    });

    expect(driver.getCurrentState().posture).toBe('DEFENSIVE');
  });

  test('DEGRADED posture for degraded health', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth({ degraded: true }));

    expect(driver.getCurrentState().posture).toBe('DEGRADED');
  });

  test('LOW_BATTERY comfort flag on critical battery', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth({ batteryBand: 'CRITICAL' }));

    expect(driver.getCurrentState().comfortFlags).toContain('LOW_BATTERY');
  });

  test('UNSTABLE_NETWORK comfort flag on weak connectivity', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth({ connectivityBand: 'WEAK' }));

    expect(driver.getCurrentState().comfortFlags).toContain('UNSTABLE_NETWORK');
  });

  test('onPhysiologyChange listener fires', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });
    const states: any[] = [];
    driver.onPhysiologyChange(s => states.push(s));

    driver.updateHealth(mkHealth());
    expect(states).toHaveLength(1);
  });

  test('unsubscribe stops listener', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });
    const states: any[] = [];
    const unsub = driver.onPhysiologyChange(s => states.push(s));

    driver.updateHealth(mkHealth());
    expect(states).toHaveLength(1);

    unsub();
    driver.updateHealth(mkHealth());
    expect(states).toHaveLength(1);
  });

  test('glow profile matches posture', () => {
    const driver = createPhysiologyDriver({ nodeId: 'n-test', transport: mockTransport() });

    driver.updateHealth(mkHealth());
    driver.updateContinuitySignals({
      riskTier: NodeRiskTier.LOW,
      operatorAttention: 0.5,
      emotionalTrajectory: 'stable',
    });

    const glow = driver.getCurrentState().glowProfile;
    expect(glow.motionPattern).toBe('breathe');
    expect(glow.intensity).toBeCloseTo(0.6);
  });
});
