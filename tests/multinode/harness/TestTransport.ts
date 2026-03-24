import type { NodeAgentTransport, TransportResponse } from "../../../node-agent/src/NodeAgent.transport";
import type { OrchestratorStub, CapabilityMap, ExpressiveState } from "./OrchestratorStub";
import type { TestNetwork } from "./TestNetwork";

/**
 * Test transport that bridges the real NodeAgent to the OrchestratorStub.
 *
 * Routes POST requests through the TestNetwork (partition-aware) into
 * OrchestratorStub methods, adapting the real agent's rich types
 * (Capability[], GlowState, AttentionState) to the harness's simplified
 * types (CapabilityMap, string-based ExpressiveState).
 *
 * The /daedalus/mirror/join path is a deliberate no-op: NodeSpawner
 * already registers the node via recordJoin before agent.start() fires.
 */
export class TestTransport implements NodeAgentTransport {
  private readonly nodeId: string;
  private readonly orchestrator: OrchestratorStub;
  private readonly network: TestNetwork;

  constructor(
    config: { nodeId: string },
    deps: { orchestrator: OrchestratorStub; network: TestNetwork },
  ) {
    this.nodeId = config.nodeId;
    this.orchestrator = deps.orchestrator;
    this.network = deps.network;
  }

  async post<T = unknown>(path: string, body: any): Promise<TransportResponse<T>> {
    if (this.network.isBlocked(this.nodeId)) {
      return { ok: false, status: 503, data: null, error: "blocked" };
    }

    try {
      this.route(path, body);
      return { ok: true, status: 200, data: null, error: null };
    } catch (err: any) {
      return { ok: false, status: 500, data: null, error: err?.message ?? "unknown" };
    }
  }

  async get<T = unknown>(_path: string): Promise<TransportResponse<T>> {
    if (this.network.isBlocked(this.nodeId)) {
      return { ok: false, status: 503, data: null, error: "blocked" };
    }
    return { ok: true, status: 200, data: null, error: null };
  }

  private route(path: string, body: any): void {
    switch (path) {
      case "/daedalus/mirror/join":
        break;

      case "/daedalus/mirror/heartbeat":
        this.orchestrator.recordHeartbeat(body.nodeId);
        break;

      case "/daedalus/mirror/caps":
        this.orchestrator.recordCapabilities(
          body.nodeId,
          this.adaptCapabilities(body.capabilities),
        );
        break;

      case "/daedalus/mirror/expressive":
        this.orchestrator.recordExpressive(
          body.nodeId,
          this.adaptExpressive(body.expressive),
        );
        break;

      case "/daedalus/mirror/profile":
        break;

      default:
        break;
    }
  }

  private adaptCapabilities(caps: any): CapabilityMap {
    if (Array.isArray(caps)) {
      const map: CapabilityMap = {};
      for (const c of caps) {
        map[c.name] = c.enabled;
      }
      return map;
    }
    return caps ?? {};
  }

  private adaptExpressive(expr: any): ExpressiveState {
    if (!expr) {
      return { glow: "baseline", posture: "neutral", affect: "calm", continuity: "fresh" };
    }
    return {
      glow: typeof expr.glow === "object" ? expr.glow.level : (expr.glow ?? "baseline"),
      posture: expr.posture ?? "neutral",
      affect: typeof expr.attention === "object"
        ? expr.attention.level
        : (expr.affect ?? "calm"),
      continuity: typeof expr.continuity === "object"
        ? (expr.continuity.healthy ? "active" : "fresh")
        : (expr.continuity ?? "fresh"),
    };
  }
}
