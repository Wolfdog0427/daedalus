import type { DeviceFingerprint } from '../../../shared/daedalus/nodeContracts';
import type { DeviceAdapter, LocalDeviceContext } from '../deviceAdapter';
import { IDLE_DEVICE_CONTEXT } from '../deviceAdapter';

export interface DesktopAdapterConfig {
  readonly deviceId: string;
  readonly model: string;
  readonly os: string;
  readonly osVersion: string;
}

export function createDesktopAdapter(config: DesktopAdapterConfig): DeviceAdapter {
  let context: LocalDeviceContext = IDLE_DEVICE_CONTEXT;
  const listeners = new Set<(ctx: LocalDeviceContext) => void>();

  return {
    getFingerprint(): DeviceFingerprint {
      return Object.freeze({
        model: config.model,
        os: config.os,
        osVersion: config.osVersion,
        deviceId: config.deviceId,
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
