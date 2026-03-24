import { createNodeRuntime } from '../src/runtime';
import type { NodeTransport } from '../src/transport';
import type { DeviceAdapter } from '../src/deviceAdapter';
import { IDLE_DEVICE_CONTEXT } from '../src/deviceAdapter';
import {
  NodeKind,
  NodeStatus,
  JoinDecisionKind,
  MOBILE_CAPABILITIES,
  NodeRiskTier,
  DeviceFingerprint,
  NodeJoinDecision,
} from '../../shared/daedalus/nodeContracts';
import type { NodeTemplateConfig } from '../src/contracts';

const fp: DeviceFingerprint = {
  model: 'TestDevice',
  os: 'android',
  osVersion: '15',
  deviceId: 'dev-rt',
};

function mkConfig(): NodeTemplateConfig {
  return {
    nodeId: 'rt-test',
    kind: NodeKind.MOBILE,
    capabilities: MOBILE_CAPABILITIES,
    operatorId: 'op-test',
    trustDomain: 'default',
    baseCadenceMs: 100,
    degradedCadenceMs: 50,
  };
}

function mkTransport(decisionKind: JoinDecisionKind): NodeTransport {
  const decision: NodeJoinDecision = {
    nodeId: 'rt-test',
    decision: decisionKind,
    reason: 'test',
    decidedAt: Date.now(),
  };
  return {
    sendJoinProposal: jest.fn().mockResolvedValue(decision),
    sendHeartbeat: jest.fn().mockResolvedValue(undefined),
    sendPhysiology: jest.fn().mockResolvedValue(undefined),
  };
}

function mkDevice(): DeviceAdapter {
  return {
    getFingerprint: () => fp,
    startSensors: jest.fn(),
    stopSensors: jest.fn(),
    onContextChange: jest.fn().mockReturnValue(() => {}),
    getCurrentContext: () => IDLE_DEVICE_CONTEXT,
  };
}

describe('createNodeRuntime', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  test('start joins and activates on APPROVED', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);

    await runtime.start();
    expect(runtime.getStatus()).toBe(NodeStatus.ACTIVE);
    expect(device.startSensors).toHaveBeenCalled();
    expect(transport.sendJoinProposal).toHaveBeenCalledTimes(1);
    runtime.stop();
  });

  test('REJECTED leaves node DETACHED, no heartbeat', async () => {
    const transport = mkTransport(JoinDecisionKind.REJECTED);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);

    await runtime.start();
    expect(runtime.getStatus()).toBe(NodeStatus.DETACHED);

    jest.advanceTimersByTime(500);
    expect(transport.sendHeartbeat).not.toHaveBeenCalled();
    runtime.stop();
  });

  test('NEEDS_OPERATOR_APPROVAL stays PENDING, no heartbeat', async () => {
    const transport = mkTransport(JoinDecisionKind.NEEDS_OPERATOR_APPROVAL);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);

    await runtime.start();
    expect(runtime.getStatus()).toBe(NodeStatus.PENDING);

    jest.advanceTimersByTime(500);
    expect(transport.sendHeartbeat).not.toHaveBeenCalled();
    runtime.stop();
  });

  test('heartbeat starts on APPROVED and emits snapshots', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);
    const snapshots: any[] = [];
    runtime.onHealthChange(s => snapshots.push(s));

    await runtime.start();
    expect(snapshots.length).toBeGreaterThan(0);
    expect(snapshots[0].nodeId).toBe('rt-test');

    jest.advanceTimersByTime(100);
    expect(snapshots.length).toBeGreaterThanOrEqual(2);
    runtime.stop();
  });

  test('stop cleans up sensors and heartbeat', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);

    await runtime.start();
    runtime.stop();
    expect(device.stopSensors).toHaveBeenCalled();

    const hbCountBefore = (transport.sendHeartbeat as jest.Mock).mock.calls.length;
    jest.advanceTimersByTime(500);
    expect((transport.sendHeartbeat as jest.Mock).mock.calls.length).toBe(hbCountBefore);
  });

  test('getHealth returns idle when no heartbeat yet', () => {
    const runtime = createNodeRuntime(
      mkConfig(),
      mkTransport(JoinDecisionKind.APPROVED),
      mkDevice(),
    );
    const health = runtime.getHealth();
    expect(health.nodeId).toBe('rt-test');
  });

  test('getPhysiology returns idle initially', () => {
    const runtime = createNodeRuntime(
      mkConfig(),
      mkTransport(JoinDecisionKind.APPROVED),
      mkDevice(),
    );
    expect(runtime.getPhysiology().posture).toBe('CALM');
  });

  test('physiology updates when heartbeat emits', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const device = mkDevice();
    const runtime = createNodeRuntime(mkConfig(), transport, device);
    const physStates: any[] = [];
    runtime.onPhysiologyChange(s => physStates.push(s));

    await runtime.start();
    expect(physStates.length).toBeGreaterThan(0);
    runtime.stop();
  });

  test('updateContinuitySignals changes physiology', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const runtime = createNodeRuntime(mkConfig(), transport, mkDevice());

    await runtime.start();
    runtime.updateContinuitySignals({
      riskTier: NodeRiskTier.HIGH,
      operatorAttention: 0.8,
      emotionalTrajectory: 'rising',
    });
    expect(runtime.getPhysiology().posture).toBe('ALERT');
    runtime.stop();
  });

  test('onStatusChange fires on join', async () => {
    const transport = mkTransport(JoinDecisionKind.APPROVED);
    const runtime = createNodeRuntime(mkConfig(), transport, mkDevice());
    const statuses: NodeStatus[] = [];
    runtime.onStatusChange(s => statuses.push(s));

    await runtime.start();
    expect(statuses).toContain(NodeStatus.ACTIVE);
    runtime.stop();
  });
});
