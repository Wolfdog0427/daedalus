import Constants from "expo-constants";
import { Platform } from "react-native";
import { IDENTITY } from "../config/identity";
import { saveContinuity } from "./continuity";
import { NodeAgent } from "../../../node-agent/src/NodeAgent";
import { createHttpTransport, type NodeAgentTransport } from "../../../node-agent/src/NodeAgent.transport";
import {
  DEFAULT_AGENT_CONFIG,
  type NodeAgentConfig,
} from "../../../node-agent/src/NodeAgent.config";
import { CANONICAL_OPERATOR_ID } from "../../../shared/daedalus/identity";
import type { AgentPhase } from "../../../node-agent/src/NodeAgent.lifecycle";

export type JoinStatus = "idle" | "joining" | "joined" | "error";

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

/** NodeAgent posts `/daedalus/mirror/*`; transport base is `{orchestrator}/daedalus`. */
function createOrchestratorTransport(orchestratorOrigin: string): NodeAgentTransport {
  const base = `${trimTrailingSlash(orchestratorOrigin)}/daedalus`;
  const token = (Constants.expoConfig?.extra as { daedalusToken?: string } | undefined)?.daedalusToken ?? "daedalus-dev-token";
  const inner = createHttpTransport(base, { token });
  return {
    post<T>(path: string, body: unknown) {
      const rel = path.startsWith("/daedalus/") ? path.slice("/daedalus".length) : path;
      return inner.post<T>(rel, body);
    },
    get<T>(path: string) {
      const rel = path.startsWith("/daedalus/") ? path.slice("/daedalus".length) : path;
      return inner.get<T>(rel);
    },
  };
}

function lifecyclePhaseToJoinStatus(phase: AgentPhase): JoinStatus {
  switch (phase) {
    case "idle":
      return "idle";
    case "joining":
      return "joining";
    case "active":
    case "degraded":
    case "disconnected":
      return "joined";
    case "error":
      return "error";
  }
}

export class PresenceClient {
  private status: JoinStatus = "idle";
  private listeners: Array<(status: JoinStatus) => void> = [];
  private readonly agent: NodeAgent;

  constructor() {
    const orchestratorUrl =
      (Constants.expoConfig?.extra as { orchestratorUrl?: string } | undefined)?.orchestratorUrl ??
      "http://10.0.2.2:3001";

    const config: NodeAgentConfig = {
      ...DEFAULT_AGENT_CONFIG,
      nodeId: IDENTITY.nodeId,
      nodeName: IDENTITY.label,
      kind: "mobile",
      model: Constants.deviceName ?? "mobile-node",
      os: Platform.OS === "ios" ? "ios" : "android",
      osVersion: String(Platform.Version),
      operatorId: CANONICAL_OPERATOR_ID,
      orchestratorUrl: trimTrailingSlash(orchestratorUrl),
      capabilities: [],
    };

    const transport = createOrchestratorTransport(orchestratorUrl);
    this.agent = new NodeAgent(config, transport);

    this.agent.lifecycle.onStateChange((s) => {
      this.setStatus(lifecyclePhaseToJoinStatus(s.phase));
    });
    this.setStatus(lifecyclePhaseToJoinStatus(this.agent.lifecycle.getState().phase));
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

  async start(): Promise<void> {
    await this.agent.start();
    if (this.agent.getPhase() === "active") {
      await saveContinuity({ lastJoinAt: new Date().toISOString() });
    }
  }

  stop(): void {
    this.agent.stop();
  }

  async sendHeartbeat(): Promise<void> {
    await this.agent.sendHeartbeat();
  }

  /** @deprecated Prefer `start()`; kept for existing call sites (e.g. DaedalusContext). */
  async sendJoinRequest() {
    await this.start();
  }
}

export function createPresenceClient() {
  return new PresenceClient();
}
