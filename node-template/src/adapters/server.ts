import type { DeviceFingerprint } from '../../../shared/daedalus/nodeContracts';
import type { DeviceAdapter, LocalDeviceContext } from '../deviceAdapter';
import { IDLE_DEVICE_CONTEXT } from '../deviceAdapter';

export interface ServerAdapterConfig {
  readonly hostname: string;
  readonly os: string;
  readonly osVersion: string;
}

export function createServerAdapter(config: ServerAdapterConfig): DeviceAdapter {
  let context: LocalDeviceContext = {
    ...IDLE_DEVICE_CONTEXT,
    batteryLevel: 1,
    networkStrength: 1,
  };
  const listeners = new Set<(ctx: LocalDeviceContext) => void>();

  return {
    getFingerprint(): DeviceFingerprint {
      return Object.freeze({
        model: 'server',
        os: config.os,
        osVersion: config.osVersion,
        deviceId: config.hostname,
      });
    },

    startSensors() {},
    stopSensors() {},

    onContextChange(handler) {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },

    getCurrentContext() {
      return context;
    },
  };
}
