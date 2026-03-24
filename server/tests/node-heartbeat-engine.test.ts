import {
  classifyBattery,
  classifyConnectivity,
  computeHeartbeatSnapshot,
  shouldDegradeHeartbeat,
  computeHeartbeatCadence,
  isHeartbeatStale,
  computeIdleHeartbeat,
  HeartbeatConfig,
  HeartbeatSignals,
  DEFAULT_HEARTBEAT_CONFIG,
} from '../../shared/daedalus/nodeHeartbeatEngine';

const cfg: HeartbeatConfig = { ...DEFAULT_HEARTBEAT_CONFIG, nodeId: 'n1' };

function mkSignals(overrides: Partial<HeartbeatSignals> = {}): HeartbeatSignals {
  return {
    batteryLevel: 0.8,
    networkStrength: 0.9,
    anomalies: [],
    ...overrides,
  };
}

describe('classifyBattery', () => {
  test('HIGH when > 0.6', () => expect(classifyBattery(0.7)).toBe('HIGH'));
  test('MEDIUM when > 0.3', () => expect(classifyBattery(0.5)).toBe('MEDIUM'));
  test('LOW when > 0.1', () => expect(classifyBattery(0.2)).toBe('LOW'));
  test('CRITICAL when <= 0.1', () => expect(classifyBattery(0.05)).toBe('CRITICAL'));
});

describe('classifyConnectivity', () => {
  test('STRONG when > 0.75', () => expect(classifyConnectivity(0.9)).toBe('STRONG'));
  test('MODERATE when > 0.4', () => expect(classifyConnectivity(0.6)).toBe('MODERATE'));
  test('WEAK when > 0.1', () => expect(classifyConnectivity(0.2)).toBe('WEAK'));
  test('OFFLINE when <= 0.1', () => expect(classifyConnectivity(0)).toBe('OFFLINE'));
});

describe('computeHeartbeatSnapshot', () => {
  test('normal snapshot', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals());
    expect(snap.nodeId).toBe('n1');
    expect(snap.liveness).toBe(true);
    expect(snap.batteryBand).toBe('HIGH');
    expect(snap.connectivityBand).toBe('STRONG');
    expect(snap.degraded).toBe(false);
    expect(snap.anomalySummary).toBeNull();
  });

  test('degraded on weak connectivity', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ networkStrength: 0.15 }));
    expect(snap.degraded).toBe(true);
    expect(snap.connectivityBand).toBe('WEAK');
  });

  test('degraded on critical battery', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ batteryLevel: 0.05 }));
    expect(snap.degraded).toBe(true);
    expect(snap.batteryBand).toBe('CRITICAL');
  });

  test('offline means not live', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ networkStrength: 0 }));
    expect(snap.liveness).toBe(false);
  });

  test('anomalies captured', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ anomalies: ['spike', 'drift'] }));
    expect(snap.anomalySummary).toBe('spike; drift');
  });

  test('snapshot is frozen', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals());
    expect(Object.isFrozen(snap)).toBe(true);
  });
});

describe('shouldDegradeHeartbeat', () => {
  test('true when degraded', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ networkStrength: 0.15 }));
    expect(shouldDegradeHeartbeat(snap)).toBe(true);
  });

  test('false when healthy', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals());
    expect(shouldDegradeHeartbeat(snap)).toBe(false);
  });
});

describe('computeHeartbeatCadence', () => {
  test('base cadence when healthy', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals());
    expect(computeHeartbeatCadence(snap, cfg)).toBe(cfg.baseCadenceMs);
  });

  test('degraded cadence when degraded', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals({ networkStrength: 0 }));
    expect(computeHeartbeatCadence(snap, cfg)).toBe(cfg.degradedCadenceMs);
  });
});

describe('isHeartbeatStale', () => {
  test('not stale when recent', () => {
    const snap = computeHeartbeatSnapshot(cfg, mkSignals());
    expect(isHeartbeatStale(snap, 30000)).toBe(false);
  });

  test('stale when timestamp is old', () => {
    const snap = { ...computeHeartbeatSnapshot(cfg, mkSignals()), timestamp: Date.now() - 60000 };
    expect(isHeartbeatStale(snap, 30000)).toBe(true);
  });
});

describe('computeIdleHeartbeat', () => {
  test('has correct nodeId', () => {
    const idle = computeIdleHeartbeat('x');
    expect(idle.nodeId).toBe('x');
    expect(idle.liveness).toBe(false);
  });
});
