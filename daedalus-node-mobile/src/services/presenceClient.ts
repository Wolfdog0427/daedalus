import axios from "axios";
import Constants from "expo-constants";
import { IDENTITY } from "../config/identity";
import { saveContinuity } from "./continuity";

export type JoinStatus = "idle" | "joining" | "joined" | "error";

export class PresenceClient {
  private status: JoinStatus = "idle";
  private listeners: Array<(status: JoinStatus) => void> = [];
  private presenceServerUrl: string;

  constructor() {
    this.presenceServerUrl =
      (Constants.expoConfig?.extra as any)?.presenceServerUrl ??
      "http://10.0.2.2:4001";
  }

  subscribe(listener: (status: JoinStatus) => void) {
    this.listeners.push(listener);
    listener(this.status);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private setStatus(status: JoinStatus) {
    this.status = status;
    this.listeners.forEach((l) => l(status));
  }

  async sendJoinRequest() {
    try {
      this.setStatus("joining");
      const res = await axios.post(`${this.presenceServerUrl}/join`, {
        nodeId: IDENTITY.nodeId,
        label: IDENTITY.label,
        platform: IDENTITY.platform,
        deviceType: IDENTITY.deviceType,
        operator: IDENTITY.operator,
        requestedAt: new Date().toISOString()
      });
      if (res.status === 200) {
        this.setStatus("joined");
        await saveContinuity({ lastJoinAt: new Date().toISOString() });
      } else {
        this.setStatus("error");
      }
    } catch (e) {
      console.warn("Join error", e);
      this.setStatus("error");
    }
  }
}

export function createPresenceClient() {
  return new PresenceClient();
}
