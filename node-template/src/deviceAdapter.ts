import type { BatteryBand, ConnectivityBand, DeviceFingerprint } from '../../shared/daedalus/nodeContracts';

export type ThermalState = 'nominal' | 'warm' | 'hot' | 'critical';

export interface LocalDeviceContext {
  readonly batteryLevel: number;
  readonly networkStrength: number;
  readonly thermalState: ThermalState;
  readonly anomalies: readonly string[];
}

export const IDLE_DEVICE_CONTEXT: LocalDeviceContext = Object.freeze({
  batteryLevel: 1,
  networkStrength: 1,
  thermalState: 'nominal' as ThermalState,
  anomalies: Object.freeze([]) as readonly string[],
});

export interface DeviceAdapter {
  getFingerprint(): DeviceFingerprint;
  startSensors(): void;
  stopSensors(): void;
  onContextChange(handler: (ctx: LocalDeviceContext) => void): () => void;
  getCurrentContext(): LocalDeviceContext;
}
