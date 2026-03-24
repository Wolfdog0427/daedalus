import {
  NodeId,
  NodeHealthSnapshot,
  BatteryBand,
  ConnectivityBand,
  NODE_HEALTH_IDLE,
} from './nodeContracts';

export interface HeartbeatSignals {
  readonly batteryLevel: number;
  readonly networkStrength: number;
  readonly anomalies: readonly string[];
}

export interface HeartbeatConfig {
  readonly nodeId: NodeId;
  readonly baseCadenceMs: number;
  readonly degradedCadenceMs: number;
  readonly degradedThreshold: number;
}

export const DEFAULT_HEARTBEAT_CONFIG: HeartbeatConfig = Object.freeze({
  nodeId: '',
  baseCadenceMs: 15000,
  degradedCadenceMs: 5000,
  degradedThreshold: 3,
});

export function classifyBattery(level: number): BatteryBand {
  if (level > 0.6) return 'HIGH';
  if (level > 0.3) return 'MEDIUM';
  if (level > 0.1) return 'LOW';
  return 'CRITICAL';
}

export function classifyConnectivity(strength: number): ConnectivityBand {
  if (strength > 0.75) return 'STRONG';
  if (strength > 0.4) return 'MODERATE';
  if (strength > 0.1) return 'WEAK';
  return 'OFFLINE';
}

export function computeHeartbeatSnapshot(
  config: HeartbeatConfig,
  signals: HeartbeatSignals,
): NodeHealthSnapshot {
  const batteryBand = classifyBattery(signals.batteryLevel);
  const connectivityBand = classifyConnectivity(signals.networkStrength);
  const degraded =
    connectivityBand === 'WEAK' ||
    connectivityBand === 'OFFLINE' ||
    batteryBand === 'CRITICAL';
  const anomalySummary =
    signals.anomalies.length > 0 ? signals.anomalies.join('; ') : null;

  return Object.freeze({
    nodeId: config.nodeId,
    liveness: connectivityBand !== 'OFFLINE',
    batteryBand,
    connectivityBand,
    anomalySummary,
    degraded,
    timestamp: Date.now(),
  });
}

export function shouldDegradeHeartbeat(snapshot: NodeHealthSnapshot): boolean {
  return snapshot.degraded;
}

export function computeHeartbeatCadence(
  snapshot: NodeHealthSnapshot,
  config: HeartbeatConfig,
): number {
  return snapshot.degraded ? config.degradedCadenceMs : config.baseCadenceMs;
}

export function isHeartbeatStale(
  snapshot: NodeHealthSnapshot,
  maxAgeMs: number,
): boolean {
  return Date.now() - snapshot.timestamp > maxAgeMs;
}

export function computeIdleHeartbeat(nodeId: NodeId): NodeHealthSnapshot {
  return Object.freeze({ ...NODE_HEALTH_IDLE, nodeId, timestamp: Date.now() });
}
