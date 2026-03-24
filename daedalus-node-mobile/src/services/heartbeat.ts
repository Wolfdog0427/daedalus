import axios from "axios";
import Constants from "expo-constants";
import { IDENTITY } from "../config/identity";
import { saveContinuity } from "./continuity";

const HEARTBEAT_INTERVAL_MS = 15_000;

export type HeartbeatStatus = "idle" | "sending" | "ok" | "error";

export class HeartbeatEngine {
  private timer: NodeJS.Timer | null = null;
  private status: HeartbeatStatus = "idle";
  private listeners: Array<(status: HeartbeatStatus) => void> = [];

  constructor(private presenceServerUrl: string) {}

  subscribe(listener: (status: HeartbeatStatus) => void) {
    this.listeners.push(listener);
    listener(this.status);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private setStatus(status: HeartbeatStatus) {
    this.status = status;
    this.listeners.forEach((l) => l(status));
  }

  start() {
    if (this.timer) return;
    this.timer = setInterval(() => {
      void this.sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);
    void this.sendHeartbeat();
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.setStatus("idle");
  }

  private async sendHeartbeat() {
    try {
      this.setStatus("sending");
      await axios.post(`${this.presenceServerUrl}/heartbeat`, {
        nodeId: IDENTITY.nodeId,
        label: IDENTITY.label,
        platform: IDENTITY.platform,
        deviceType: IDENTITY.deviceType,
        operator: IDENTITY.operator,
        timestamp: new Date().toISOString()
      });
      await saveContinuity({ lastHeartbeatAt: new Date().toISOString() });
      this.setStatus("ok");
    } catch (e) {
      console.warn("Heartbeat error", e);
      this.setStatus("error");
    }
  }
}

export function createHeartbeatEngine() {
  const presenceServerUrl =
    (Constants.expoConfig?.extra as any)?.presenceServerUrl ??
    "http://10.0.2.2:4001";
  return new HeartbeatEngine(presenceServerUrl);
}
