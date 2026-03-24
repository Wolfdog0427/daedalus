import request from "supertest";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload } from "../orchestrator/mirror";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { GovernanceService, governanceService } from "../orchestrator/governance/GovernanceService";
import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

function mkJoin(id: string, overrides?: any): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server",
      model: "test-model",
      os: "linux",
      osVersion: "6.1",
      operatorId: "op1",
    },
    capabilities: [
      { name: "vision", value: "enabled", enabled: true },
      { name: "audio", value: "disabled", enabled: false },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
    ...overrides,
  };
}

function mkHeartbeat(id: string): NodeHeartbeatPayload {
  return { nodeId: id, timestamp: new Date().toISOString(), status: "alive" };
}

// ─── SCENARIO: Critical node flapping, governance escalates, operator intervenes ──

describe("Incident Rehearsal: flapping node → governance escalation → operator recovery", () => {
  let app: ReturnType<typeof createOrchestratorApp>;
  let reg: NodeMirrorRegistry;
  let govSvc: GovernanceService;
  let allEvents: DaedalusEventPayload[];
  let appliedOverrideId: string;

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();

    allEvents = [];
    const bus = getDaedalusEventBus();
    bus.subscribe((e) => allEvents.push(e));

    reg = getNodeMirrorRegistry();
    govSvc = new GovernanceService();
    app = createOrchestratorApp();

    const nodeIds = ["core-1", "core-2", "worker-1", "worker-2", "worker-3"];
    for (const id of nodeIds) {
      reg.handleJoin(mkJoin(id));
      reg.handleHeartbeat(mkHeartbeat(id));
    }
  });

  test("Step 1: worker-3 starts flapping (errors accumulate)", () => {
    for (let i = 0; i < 3; i++) {
      reg.handleError("worker-3", `Transient error ${i + 1}`);
    }
    const mirror = reg.getMirror("worker-3");
    expect(mirror).toBeDefined();
    expect(mirror!.lifecycle.errorCount).toBe(3);
    expect(mirror!.lifecycle.phase).toBe("active");
  });

  test("Step 2: flapping continues, auto-quarantine triggers", () => {
    reg.handleError("worker-3", "Transient error 4");
    reg.handleError("worker-3", "Transient error 5");

    const mirror = reg.getMirror("worker-3");
    expect(mirror).toBeDefined();
    expect(mirror!.lifecycle.errorCount).toBeGreaterThanOrEqual(5);
    expect(mirror!.lifecycle.phase).toBe("quarantined");
  });

  test("Step 3: governance posture reflects the incident", () => {
    govSvc.recordDrift({
      severity: "HIGH",
      summary: "Node worker-3 quarantined due to persistent errors",
    });
    expect(govSvc.getPostureSnapshot().posture).toBe("GUARDED");
  });

  test("Step 4: operator applies GLOBAL ESCALATE override", () => {
    const override = govSvc.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
      reason: "Incident response: escalate monitoring",
      scope: "GLOBAL",
      effect: "ESCALATE",
    });
    appliedOverrideId = override.id;
    expect(govSvc.getPostureSnapshot().posture).toBe("GUARDED");
  });

  test("Step 5: cockpit shows the full picture", async () => {
    const nodesRes = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    const worker3 = nodesRes.body.find((n: any) => n.id === "worker-3");
    expect(worker3).toBeDefined();
    expect(worker3.status).toMatch(/quarantined|suspended/);

    const summaryRes = await request(app).get("/daedalus/cockpit/summary").expect(200);
    const byStatus = summaryRes.body.byStatus;
    expect(byStatus).toBeDefined();

    const postureRes = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(postureRes.body.posture).toBe("OPEN");
  });

  test("Step 6: operator quarantines worker-3 explicitly (no-op)", async () => {
    const res = await request(app)
      .post("/daedalus/mirror/quarantine")
      .send({ nodeId: "worker-3" })
      .expect(200);
    expect(res.body.quarantined).toBe(true);

    const mirror = reg.getMirror("worker-3");
    expect(mirror!.lifecycle.phase).toBe("quarantined");
  });

  test("Step 7: operator heals the system", () => {
    const removed = govSvc.removeOverride(appliedOverrideId);
    expect(removed).toBe(true);
    govSvc.clearDrifts();
    expect(govSvc.getPostureSnapshot().posture).toBe("OPEN");
  });

  test("Step 8: node worker-3 detaches and rejoins after fix", () => {
    reg.handleDetach("worker-3");
    reg.handleJoin(mkJoin("worker-3"));
    const hb = reg.handleHeartbeat(mkHeartbeat("worker-3"));
    expect(hb).not.toBeNull();
    const mirror = reg.getMirror("worker-3");
    expect(mirror!.lifecycle.phase).toBe("active");
    expect(mirror!.lifecycle.errorCount).toBe(0);
  });

  test("Step 9: continuity recovers", () => {
    const beings = daedalusStore.getBeingPresences();
    const operator = beings.find((b) => b.id === "operator");
    expect(operator).toBeDefined();
    expect(operator!.continuity.healthy).toBe(true);

    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  test("Step 10: event log tells a coherent story", () => {
    const types = allEvents.map((e) => e.type);

    expect(types).toContain("MIRROR_NODE_JOINED");
    expect(types).toContain("MIRROR_NODE_HEARTBEAT");
    expect(types).toContain("MIRROR_NODE_ERROR");
    expect(types).toContain("MIRROR_NODE_QUARANTINED");

    const errorEvents = allEvents.filter(
      (e) => e.type === "MIRROR_NODE_ERROR" && e.nodeId === "worker-3",
    );
    expect(errorEvents.length).toBeGreaterThanOrEqual(5);

    const quarantineEvents = allEvents.filter(
      (e) => e.type === "MIRROR_NODE_QUARANTINED" && e.nodeId === "worker-3",
    );
    expect(quarantineEvents.length).toBeGreaterThanOrEqual(1);

    const joinEvents = allEvents.filter((e) => e.type === "MIRROR_NODE_JOINED");
    const lastJoin = joinEvents[joinEvents.length - 1];
    expect(lastJoin.nodeId).toBe("worker-3");

    for (let i = 1; i < allEvents.length; i++) {
      expect(allEvents[i].timestamp >= allEvents[i - 1].timestamp).toBe(true);
    }
  });
});
