import request from "supertest";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload } from "../orchestrator/mirror";
import { resetDaedalusEventBus } from "../orchestrator/DaedalusEventBus";
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
    ],
    expressive: { ...IDLE_EXPRESSIVE },
    ...overrides,
  };
}

// ─── UNICODE / WEIRD IDS ────────────────────────────────────────────

describe("UNICODE / WEIRD IDS", () => {
  let reg: NodeMirrorRegistry;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = new NodeMirrorRegistry();
  });

  test("node ID with spaces: join and heartbeat work", () => {
    const id = "node with spaces";
    reg.handleJoin(mkJoin(id));
    const hb = reg.handleHeartbeat({
      nodeId: id,
      timestamp: new Date().toISOString(),
      status: "alive",
    });
    expect(hb).not.toBeNull();
    expect(reg.getMirror(id)).toBeDefined();
  });

  test("node ID with unicode: join and heartbeat work", () => {
    const id = "nöde-αβγ-日本語";
    reg.handleJoin(mkJoin(id));
    const hb = reg.handleHeartbeat({
      nodeId: id,
      timestamp: new Date().toISOString(),
      status: "alive",
    });
    expect(hb).not.toBeNull();
    expect(reg.getMirror(id)!.id).toBe(id);
  });

  test("node ID with very long string (500 chars): works", () => {
    const id = "x".repeat(500);
    reg.handleJoin(mkJoin(id));
    expect(reg.getMirror(id)).toBeDefined();
    expect(reg.getMirror(id)!.id).toBe(id);
  });

  test("being name with emojis: update and retrieve", () => {
    const updated = daedalusStore.updateBeingPresence("operator", {
      name: "Guardian 🛡️✨",
    });
    expect(updated).not.toBeNull();
    expect(updated!.name).toBe("Guardian 🛡️✨");
    const retrieved = daedalusStore.getBeingPresence("operator");
    expect(retrieved!.name).toBe("Guardian 🛡️✨");
  });

  test("being name with non-Latin scripts: preserved", () => {
    const updated = daedalusStore.updateBeingPresence("operator", {
      name: "ストラテジー",
    });
    expect(updated).not.toBeNull();
    expect(updated!.name).toBe("ストラテジー");
    const retrieved = daedalusStore.getBeingPresence("operator");
    expect(retrieved!.name).toBe("ストラテジー");
  });

  test("empty string nodeId: join returns appropriate error", () => {
    const app = createOrchestratorApp();
    return request(app)
      .post("/daedalus/mirror/join")
      .send(mkJoin(""))
      .expect((res) => {
        expect([400, 201]).toContain(res.status);
      });
  });

  test("null/undefined fields in payloads: no server crash", () => {
    const app = createOrchestratorApp();
    return request(app)
      .post("/daedalus/mirror/join")
      .send({ nodeId: "null-test", name: null, capabilities: null, expressive: null })
      .expect(400);
  });
});

// ─── EMPTY-WORLD TESTS ──────────────────────────────────────────────

describe("EMPTY-WORLD TESTS", () => {
  let app: ReturnType<typeof createOrchestratorApp>;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    app = createOrchestratorApp();
  });

  test("no nodes, no overrides: cockpit doesn't crash", async () => {
    const nodesRes = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    expect(nodesRes.body).toEqual([]);

    const summaryRes = await request(app).get("/daedalus/cockpit/summary").expect(200);
    expect(summaryRes.body.totalNodes).toBe(0);
  });

  test("no nodes: snapshot returns valid structure", async () => {
    const res = await request(app).get("/daedalus/snapshot").expect(200);
    expect(res.body.nodes).toEqual([]);
    expect(res.body.beings).toBeDefined();
    expect(res.body.beings.length).toBeGreaterThan(0);
  });

  test("no nodes: governance posture is OPEN", async () => {
    const svc = new GovernanceService();
    const snapshot = svc.getPostureSnapshot();
    expect(snapshot.posture).toBe("OPEN");
  });

  test("no overrides, no votes, no drifts: posture OPEN", async () => {
    const res = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(res.body.posture).toBe("OPEN");
  });

  test("only operator being exists: constitution passes", () => {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  test("empty world: continuity not labeled degraded", () => {
    const beings = daedalusStore.getBeingPresences();
    const operator = beings.find((b) => b.id === "operator");
    expect(operator).toBeDefined();
    expect(operator!.continuity.healthy).toBe(true);
  });
});

// ─── MAXIMAL-WORLD TESTS ────────────────────────────────────────────

describe("MAXIMAL-WORLD TESTS", () => {
  let app: ReturnType<typeof createOrchestratorApp>;
  let reg: NodeMirrorRegistry;
  let govSvc: GovernanceService;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    app = createOrchestratorApp();
    reg = getNodeMirrorRegistry();
    govSvc = new GovernanceService();
  });

  function seedMaximalWorld() {
    for (let i = 0; i < 500; i++) {
      reg.handleJoin(mkJoin(`max-${i}`));
    }
    for (let i = 0; i < 50; i++) {
      govSvc.applyOverride({
        createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
        reason: `Override ${i}`,
        scope: "NODE",
        targetId: `max-${i}`,
        effect: "ALLOW",
      });
    }
    for (let i = 0; i < 50; i++) {
      govSvc.castVote({
        being: { id: `voter-${i}`, role: "GUARDIAN", label: `Guardian ${i}` },
        vote: "ALLOW",
        weight: 0.3,
      });
    }
    for (let i = 0; i < 20; i++) {
      govSvc.recordDrift({
        severity: "LOW",
        summary: `Low drift ${i}`,
      });
    }
  }

  test("500 nodes + 50 overrides + 50 votes + 20 drifts: system stable", () => {
    seedMaximalWorld();
    const snapshot = govSvc.getPostureSnapshot();
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(snapshot.posture);
    const views = reg.toCockpitView();
    expect(views.length).toBe(500);
  });

  test("maximal world: constitution still passes", () => {
    seedMaximalWorld();
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  test("maximal world: snapshot returns complete data", async () => {
    seedMaximalWorld();
    const res = await request(app).get("/daedalus/snapshot").expect(200);
    expect(res.body.nodes).toBeDefined();
    expect(res.body.beings).toBeDefined();
    expect(res.body.nodes.length).toBe(500);
  });

  test("maximal world: clear all governance → posture OPEN", () => {
    seedMaximalWorld();
    govSvc.clearOverrides();
    govSvc.clearVotes();
    govSvc.clearDrifts();
    expect(govSvc.getPostureSnapshot().posture).toBe("OPEN");
  });
});
