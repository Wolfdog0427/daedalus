import { createHeartbeatEngine, HeartbeatEngineConfig } from '../src/heartbeatEngine';
import type { NodeTransport } from '../src/transport';
import type { LocalDeviceContext } from '../src/deviceAdapter';
import { IDLE_DEVICE_CONTEXT } from '../src/deviceAdapter';

function mockTransport(): NodeTransport & { heartbeats: any[] } {
  const heartbeats: any[] = [];
  return {
    heartbeats,
    sendJoinProposal: jest.fn().mockResolvedValue({}),
    sendHeartbeat: jest.fn().mockImplementation(async (snap) => { heartbeats.push(snap); }),
    sendPhysiology: jest.fn().mockResolvedValue(undefined),
  };
}

function mkConfig(transport: NodeTransport): HeartbeatEngineConfig {
  return {
    nodeId: 'test-node',
    transport,
    baseCadenceMs: 100,
    degradedCadenceMs: 50,
  };
}

describe('createHeartbeatEngine', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  test('starts and emits first snapshot immediately', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));
    const snapshots: any[] = [];
    engine.onSnapshot(s => snapshots.push(s));

    engine.start();
    expect(snapshots).toHaveLength(1);
    expect(snapshots[0].nodeId).toBe('test-node');
    expect(snapshots[0].liveness).toBe(true);
    engine.stop();
  });

  test('emits subsequent snapshots at base cadence', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));
    const snapshots: any[] = [];
    engine.onSnapshot(s => snapshots.push(s));

    engine.start();
    expect(snapshots).toHaveLength(1);

    jest.advanceTimersByTime(100);
    expect(snapshots).toHaveLength(2);

    jest.advanceTimersByTime(100);
    expect(snapshots).toHaveLength(3);
    engine.stop();
  });

  test('switches to degraded cadence on weak connectivity', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));
    const snapshots: any[] = [];
    engine.onSnapshot(s => snapshots.push(s));

    const degradedCtx: LocalDeviceContext = {
      batteryLevel: 0.8,
      networkStrength: 0.15,
      thermalState: 'nominal',
      anomalies: [],
    };
    engine.updateContext(degradedCtx);
    engine.start();

    expect(snapshots[0].degraded).toBe(true);
    expect(snapshots[0].connectivityBand).toBe('WEAK');

    jest.advanceTimersByTime(50);
    expect(snapshots).toHaveLength(2);
    engine.stop();
  });

  test('stop ceases emission', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));
    const snapshots: any[] = [];
    engine.onSnapshot(s => snapshots.push(s));

    engine.start();
    engine.stop();

    jest.advanceTimersByTime(500);
    expect(snapshots).toHaveLength(1);
  });

  test('sends heartbeat via transport', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));

    engine.start();
    expect(transport.sendHeartbeat).toHaveBeenCalledTimes(1);
    engine.stop();
  });

  test('isRunning reflects state', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));

    expect(engine.isRunning()).toBe(false);
    engine.start();
    expect(engine.isRunning()).toBe(true);
    engine.stop();
    expect(engine.isRunning()).toBe(false);
  });

  test('getLastSnapshot returns most recent', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));

    expect(engine.getLastSnapshot()).toBeNull();
    engine.start();
    expect(engine.getLastSnapshot()).not.toBeNull();
    expect(engine.getLastSnapshot()!.nodeId).toBe('test-node');
    engine.stop();
  });

  test('unsubscribe stops listener', () => {
    const transport = mockTransport();
    const engine = createHeartbeatEngine(mkConfig(transport));
    const snapshots: any[] = [];
    const unsub = engine.onSnapshot(s => snapshots.push(s));

    engine.start();
    expect(snapshots).toHaveLength(1);
    unsub();

    jest.advanceTimersByTime(100);
    expect(snapshots).toHaveLength(1);
    engine.stop();
  });
});
