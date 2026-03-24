import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload } from "../orchestrator/mirror";
import { GovernanceService, governanceService } from "../orchestrator/governance/GovernanceService";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { daedalusStore } from "../orchestrator/daedalusStore";
import type { BeingVote } from "../../shared/daedalus/contracts";

function mkJoin(id: string): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server" as const,
      model: "test",
      os: "linux",
      osVersion: "6.1",
      operatorId: "operator",
    },
  };
}

function mkOverride(scope: "NODE" | "CAPABILITY" | "GLOBAL" = "NODE", effect: "ALLOW" | "DENY" | "ESCALATE" = "ALLOW") {
  return {
    createdBy: { id: "op", role: "OPERATOR" as const, label: "Operator" },
    reason: `test-override-${scope}-${effect}`,
    scope,
    targetId: scope !== "GLOBAL" ? "n1" : undefined,
    effect,
  };
}

// ─── Governance Abuse ────────────────────────────────────────────────

describe("Governance Abuse", () => {
  let svc: GovernanceService;

  beforeEach(() => {
    svc = new GovernanceService();
    resetDaedalusEventBus();
  });

  test("override spam: 100 rapid overrides don't crash", () => {
    for (let i = 0; i < 100; i++) {
      svc.applyOverride({
        createdBy: { id: `op-${i}`, role: "OPERATOR", label: `Op${i}` },
        reason: `spam-${i}`,
        scope: "NODE",
        targetId: `n-${i}`,
        effect: "ALLOW",
      });
    }

    const snapshot = svc.getPostureSnapshot();
    expect(snapshot.posture).toBeDefined();
    expect(typeof snapshot.posture).toBe("string");
    expect(svc.listOverrides()).toHaveLength(100);

    const snap2 = svc.getPostureSnapshot();
    expect(snap2.posture).toBe(snapshot.posture);
  });

  test("conflicting scope overrides: GLOBAL DENY + NODE ALLOW", () => {
    svc.applyOverride(mkOverride("GLOBAL", "DENY"));
    svc.applyOverride(mkOverride("NODE", "ALLOW"));

    expect(svc.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("vote spam: 51 votes from fake beings, only 50 accepted", () => {
    for (let i = 0; i < 51; i++) {
      svc.castVote({
        being: { id: `being-${i}`, role: "GUARDIAN", label: `B${i}` },
        vote: "ALLOW",
        weight: 0.5,
      });
    }

    expect(svc.listVotes()).toHaveLength(50);
  });

  test("perpetual LOCKDOWN attempt via votes", () => {
    for (let i = 0; i < 10; i++) {
      svc.castVote({
        being: { id: `deny-being-${i}`, role: "SENTINEL", label: `D${i}` },
        vote: "DENY",
        weight: 1.0,
      });
    }

    expect(svc.getPostureSnapshot().posture).toBe("LOCKDOWN");

    svc.clearVotes();
    expect(svc.getPostureSnapshot().posture).toBe("OPEN");
  });

  test("posture thrash detection: rapid override create/remove", () => {
    const bus = getDaedalusEventBus();
    const postureChanges: DaedalusEventPayload[] = [];
    bus.subscribe((e) => {
      if (e.type === "POSTURE_CHANGED") postureChanges.push(e);
    });

    for (let i = 0; i < 50; i++) {
      const o = svc.applyOverride({
        createdBy: { id: "op", role: "OPERATOR", label: "Op" },
        reason: `thrash-${i}`,
        scope: "GLOBAL",
        effect: "DENY",
      });
      svc.removeOverride(o.id);
    }

    expect(postureChanges.length).toBeLessThanOrEqual(200);
    expect(postureChanges.length).toBeGreaterThan(0);

    const finalPosture = svc.getPostureSnapshot().posture;
    expect(finalPosture).toBe("OPEN");
  });
});

// ─── Node Impersonation ─────────────────────────────────────────────

describe("Node Impersonation", () => {
  const app = createOrchestratorApp();

  beforeEach(() => {
    resetNodeMirrorRegistry();
  });

  test("duplicate nodeId join: second join re-syncs the existing active node", async () => {
    const join1 = { ...mkJoin("dup-node"), profile: { ...mkJoin("dup-node").profile, model: "first-model" } };
    await request(app).post("/daedalus/mirror/join").send(join1).expect(201);

    const join2 = { ...mkJoin("dup-node"), profile: { ...mkJoin("dup-node").profile, model: "second-model" } };
    await request(app).post("/daedalus/mirror/join").send(join2).expect(201);

    const reg = getNodeMirrorRegistry();
    const mirror = reg.getMirror("dup-node");
    expect(mirror).toBeDefined();
    expect(mirror!.profile.model).toBe("second-model");
    expect(mirror!.lifecycle.phase).toBe("active");
  });

  test("heartbeat for never-joined node: 404", async () => {
    await request(app)
      .post("/daedalus/mirror/heartbeat")
      .send({ nodeId: "never-joined-xyz", timestamp: new Date().toISOString(), status: "alive" })
      .expect(404);
  });

  test("malformed join payload: missing capabilities → 400", async () => {
    const payload = { nodeId: "bad-1", name: "Bad Node", expressive: { ...IDLE_EXPRESSIVE }, profile: mkJoin("bad-1").profile };
    await request(app).post("/daedalus/mirror/join").send(payload).expect(400);
  });

  test("malformed join payload: capabilities not array → 400", async () => {
    const payload = {
      nodeId: "bad-2",
      name: "Bad Node",
      capabilities: "string-not-array",
      expressive: { ...IDLE_EXPRESSIVE },
      profile: mkJoin("bad-2").profile,
    };
    await request(app).post("/daedalus/mirror/join").send(payload).expect(400);
  });

  test("malformed expressive payload: null → 400", async () => {
    const payload = {
      nodeId: "bad-3",
      name: "Bad Node",
      capabilities: [{ name: "core", value: "enabled", enabled: true }],
      expressive: null,
      profile: mkJoin("bad-3").profile,
    };
    await request(app).post("/daedalus/mirror/join").send(payload).expect(400);
  });

  test("XSS in node name: stored but not interpreted", async () => {
    const xssName = `<script>alert('x')</script>`;
    const join = { ...mkJoin("xss-node"), name: xssName };

    await request(app).post("/daedalus/mirror/join").send(join).expect(201);

    const reg = getNodeMirrorRegistry();
    const mirror = reg.getMirror("xss-node");
    expect(mirror).toBeDefined();
    expect(mirror!.name).toBe(xssName);
    expect(typeof mirror!.name).toBe("string");
  });
});

// ─── Being Impersonation ────────────────────────────────────────────

describe("Being Impersonation", () => {
  const app = createOrchestratorApp();

  beforeEach(() => {
    resetDaedalusEventBus();
  });

  test("vote for non-existent being: accepted but posture computation sane", () => {
    const svc = new GovernanceService();
    svc.castVote({
      being: { id: "fake-being-xyz", role: "GUARDIAN", label: "Ghost" },
      vote: "ALLOW",
      weight: 0.3,
    });

    expect(svc.listVotes()).toHaveLength(1);
    expect(svc.listVotes()[0].being.id).toBe("fake-being-xyz");

    const snapshot = svc.getPostureSnapshot();
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(snapshot.posture);
  });

  test("update reserved 'operator' being: allowed (it exists)", async () => {
    const res = await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ presenceMode: "dominant" })
      .expect(200);

    expect(res.body.id).toBe("operator");
    expect(res.body.presenceMode).toBe("dominant");
  });

  test("update non-existent being: 404", async () => {
    await request(app)
      .put("/daedalus/beings/nonexistent/presence")
      .send({ presenceMode: "idle" })
      .expect(404);
  });

  test("constitution still holds after adversarial inputs", () => {
    const svc = new GovernanceService();

    for (let i = 0; i < 20; i++) {
      svc.applyOverride({
        createdBy: { id: `adv-${i}`, role: "OPERATOR", label: `Adv${i}` },
        reason: `adversarial-${i}`,
        scope: i % 3 === 0 ? "GLOBAL" : "NODE",
        targetId: i % 3 !== 0 ? `node-${i}` : undefined,
        effect: i % 2 === 0 ? "DENY" : "ALLOW",
      });
    }

    for (let i = 0; i < 50; i++) {
      svc.castVote({
        being: { id: `voter-${i}`, role: "GUARDIAN", label: `V${i}` },
        vote: i % 2 === 0 ? "DENY" : "ALLOW",
        weight: Math.random(),
      });
    }

    for (let i = 0; i < 10; i++) {
      svc.recordDrift({
        severity: (["LOW", "MEDIUM", "HIGH"] as const)[i % 3],
        summary: `drift-${i}`,
      });
    }

    const beings = daedalusStore.getBeingPresences();
    const votes = svc.listVotes();
    const report = validateBeingConstitution(beings, votes);

    expect(report).toBeDefined();
    expect(report.checks).toHaveLength(10);
    expect(typeof report.allPassed).toBe("boolean");

    const operatorCheck = report.checks.find((c) => c.name === "operator-always-present");
    expect(operatorCheck?.passed).toBe(true);
  });
});
