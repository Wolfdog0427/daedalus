import type { NodeId, NodeHealthSnapshot } from '../../shared/daedalus/nodeContracts';
import {
  computeHeartbeatSnapshot,
  computeHeartbeatCadence,
  HeartbeatConfig,
  DEFAULT_HEARTBEAT_CONFIG,
} from '../../shared/daedalus/nodeHeartbeatEngine';
import type { NodeTransport } from './transport';
import type { LocalDeviceContext } from './deviceAdapter';
import { IDLE_DEVICE_CONTEXT } from './deviceAdapter';

export interface HeartbeatEngineConfig {
  readonly nodeId: NodeId;
  readonly transport: NodeTransport;
  readonly baseCadenceMs: number;
  readonly degradedCadenceMs: number;
}

export function createHeartbeatEngine(config: HeartbeatEngineConfig) {
  const hbConfig: HeartbeatConfig = {
    ...DEFAULT_HEARTBEAT_CONFIG,
    nodeId: config.nodeId,
    baseCadenceMs: config.baseCadenceMs,
    degradedCadenceMs: config.degradedCadenceMs,
  };

  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = false;
  let currentContext: LocalDeviceContext = IDLE_DEVICE_CONTEXT;
  let lastSnapshot: NodeHealthSnapshot | null = null;
  const listeners = new Set<(snapshot: NodeHealthSnapshot) => void>();

  function emit() {
    const snapshot = computeHeartbeatSnapshot(hbConfig, {
      batteryLevel: currentContext.batteryLevel,
      networkStrength: currentContext.networkStrength,
      anomalies: currentContext.anomalies,
    });
    lastSnapshot = snapshot;
    for (const fn of listeners) fn(snapshot);
    config.transport.sendHeartbeat(snapshot).catch(() => {});
    scheduleNext(snapshot);
  }

  function scheduleNext(snapshot: NodeHealthSnapshot) {
    if (!running) return;
    const cadence = computeHeartbeatCadence(snapshot, hbConfig);
    timer = setTimeout(emit, cadence);
  }

  return {
    start() {
      if (running) return;
      running = true;
      emit();
    },

    stop() {
      running = false;
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
    },

    isRunning() {
      return running;
    },

    updateContext(ctx: LocalDeviceContext) {
      currentContext = ctx;
    },

    getLastSnapshot(): NodeHealthSnapshot | null {
      return lastSnapshot;
    },

    onSnapshot(handler: (snapshot: NodeHealthSnapshot) => void): () => void {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },
  };
}

export type HeartbeatEngine = ReturnType<typeof createHeartbeatEngine>;
