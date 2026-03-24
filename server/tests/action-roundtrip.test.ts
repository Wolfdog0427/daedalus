import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import type { NodeJoinPayload } from "../orchestrator/mirror";

const app = createOrchestratorApp();

function mkJoinPayload(id = "rt-node"): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server",
      model: "test",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
    capabilities: [
      { name: "negotiation", value: "enabled", enabled: true },
      { name: "capability-trace", value: "enabled", enabled: true },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function collectEvents(): { events: DaedalusEventPayload[]; stop: () => void } {
  const events: DaedalusEventPayload[] = [];
  const unsub = getDaedalusEventBus().subscribe((e) => events.push(e));
  return { events, stop: unsub };
}

beforeEach(() => {
  resetNodeMirrorRegistry();
  resetDaedalusEventBus();
  governanceService.clearOverrides();
  governanceService.clearDrifts();
  governanceService.clearVotes();
});

// ─── Override Lifecycle Round-Trip ─────────────────────────────────────

describe("Override lifecycle round-trip", () => {
  test("create override → state changes → event emitted → cockpit reflects", async () => {
    const collector = collectEvents();

    const createRes = await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: "Tighten node scope",
        scope: "NODE",
        targetId: "n1",
        effect: "ALLOW",
      })
      .expect(201);

    expect(createRes.body.id).toBeDefined();
    const overrideId = createRes.body.id;

    const listRes = await request(app)
      .get("/daedalus/governance/overrides")
      .expect(200);
    expect(listRes.body.some((o: any) => o.id === overrideId)).toBe(true);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("ATTENTIVE");

    collector.stop();
    expect(
      collector.events.some((e) => e.type === "GOVERNANCE_OVERRIDE_APPLIED"),
    ).toBe(true);
  });

  test("remove override → state reverts → event emitted", async () => {
    const createRes = await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: "Temporary",
        scope: "NODE",
        targetId: "n1",
        effect: "ALLOW",
      })
      .expect(201);

    const overrideId = createRes.body.id;

    const collector = collectEvents();

    await request(app)
      .delete(`/daedalus/governance/overrides/${overrideId}`)
      .expect(204);

    const listRes = await request(app)
      .get("/daedalus/governance/overrides")
      .expect(200);
    expect(listRes.body).toHaveLength(0);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("OPEN");

    collector.stop();
    expect(
      collector.events.some((e) => e.type === "POSTURE_CHANGED"),
    ).toBe(true);
  });

  test("clear overrides → all gone → posture OPEN", async () => {
    await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: "First",
        scope: "NODE",
        effect: "ALLOW",
      })
      .expect(201);

    await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: "Second",
        scope: "CAPABILITY",
        targetId: "negotiation",
        effect: "ESCALATE",
      })
      .expect(201);

    await request(app).delete("/daedalus/governance/overrides").expect(204);

    const listRes = await request(app)
      .get("/daedalus/governance/overrides")
      .expect(200);
    expect(listRes.body).toHaveLength(0);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("OPEN");
  });
});

// ─── Vote Lifecycle Round-Trip ────────────────────────────────────────

describe("Vote lifecycle round-trip", () => {
  test("cast vote → posture influenced → visible in votes list", async () => {
    const res = await request(app)
      .post("/daedalus/governance/votes")
      .send({
        being: { id: "operator", role: "OPERATOR", label: "Operator" },
        vote: "ALLOW",
        weight: 0.8,
      })
      .expect(201);

    expect(res.body.vote).toBe("ALLOW");

    const votesRes = await request(app)
      .get("/daedalus/governance/votes")
      .expect(200);
    expect(votesRes.body.length).toBeGreaterThanOrEqual(1);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("ATTENTIVE");
  });

  test("clear votes → posture returns to OPEN", async () => {
    await request(app)
      .post("/daedalus/governance/votes")
      .send({
        being: { id: "operator", role: "OPERATOR", label: "Operator" },
        vote: "DENY",
        weight: 1.0,
      })
      .expect(201);

    await request(app).delete("/daedalus/governance/votes").expect(204);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("OPEN");

    const votesRes = await request(app)
      .get("/daedalus/governance/votes")
      .expect(200);
    expect(votesRes.body).toHaveLength(0);
  });
});

// ─── Drift Lifecycle Round-Trip ───────────────────────────────────────

describe("Drift lifecycle round-trip", () => {
  test("record HIGH drift → posture GUARDED → visible in drifts", async () => {
    const collector = collectEvents();

    const res = await request(app)
      .post("/daedalus/governance/drifts")
      .send({ severity: "HIGH", summary: "Identity drift detected" })
      .expect(201);

    expect(res.body.id).toBeDefined();

    const driftsRes = await request(app)
      .get("/daedalus/governance/drifts")
      .expect(200);
    expect(driftsRes.body.some((d: any) => d.id === res.body.id)).toBe(true);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("GUARDED");

    collector.stop();
    expect(
      collector.events.some((e) => e.type === "CONTINUITY_DRIFT_DETECTED"),
    ).toBe(true);
  });

  test("clear drifts → posture OPEN", async () => {
    await request(app)
      .post("/daedalus/governance/drifts")
      .send({ severity: "HIGH", summary: "Critical drift" })
      .expect(201);

    await request(app).delete("/daedalus/governance/drifts").expect(204);

    const postureRes = await request(app)
      .get("/daedalus/governance/posture")
      .expect(200);
    expect(postureRes.body.posture).toBe("OPEN");

    const driftsRes = await request(app)
      .get("/daedalus/governance/drifts")
      .expect(200);
    expect(driftsRes.body).toHaveLength(0);
  });
});

// ─── Being Update Round-Trip ──────────────────────────────────────────

describe("Being update round-trip", () => {
  test("update being → new state → event emitted → cockpit reflects", async () => {
    const collector = collectEvents();

    const updateRes = await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ presenceMode: "dominant", isSpeaking: true })
      .expect(200);

    expect(updateRes.body.presenceMode).toBe("dominant");
    expect(updateRes.body.isSpeaking).toBe(true);

    const getRes = await request(app)
      .get("/daedalus/beings/operator/presence")
      .expect(200);
    expect(getRes.body.presenceMode).toBe("dominant");
    expect(getRes.body.isSpeaking).toBe(true);

    collector.stop();
    const beingEvents = collector.events.filter(
      (e) => e.type === "BEING_PRESENCE_UPDATED" && e.beingId === "operator",
    );
    expect(beingEvents.length).toBeGreaterThanOrEqual(1);
    expect(beingEvents[0].beingPresence!.presenceMode).toBe("dominant");
  });
});

// ─── Capability Toggle Round-Trip ─────────────────────────────────────

describe("Capability toggle round-trip", () => {
  test("toggle capability via negotiation → state changes → event emitted", async () => {
    await request(app)
      .post("/daedalus/mirror/join")
      .send(mkJoinPayload("neg-node"))
      .expect(201);

    const collector = collectEvents();

    const applyRes = await request(app)
      .post("/daedalus/negotiations/apply")
      .send({
        requestedBy: { id: "operator" },
        targetNodeId: "neg-node",
        capabilityName: "negotiation",
        desiredEnabled: false,
      })
      .expect(200);

    expect(applyRes.body.applied).toBe(true);
    expect(applyRes.body.decisions[0].toEnabled).toBe(false);

    const traceRes = await request(app)
      .get("/daedalus/capabilities/trace")
      .query({ nodeId: "neg-node", capabilityName: "negotiation" })
      .expect(200);
    expect(traceRes.body.effectiveEnabled).toBe(false);

    collector.stop();
    expect(
      collector.events.some((e) => e.type === "NEGOTIATION_COMPLETED"),
    ).toBe(true);
  });
});

// ─── Node Quarantine Round-Trip ───────────────────────────────────────

describe("Node quarantine round-trip", () => {
  test("quarantine via HTTP → mirror reflects → cockpit reflects", async () => {
    await request(app)
      .post("/daedalus/mirror/join")
      .send(mkJoinPayload("q-node"))
      .expect(201);

    await request(app)
      .post("/daedalus/mirror/quarantine")
      .send({ nodeId: "q-node" })
      .expect(200);

    const cockpitRes = await request(app)
      .get("/daedalus/cockpit/nodes")
      .expect(200);

    const node = cockpitRes.body.find((n: any) => n.id === "q-node");
    expect(node).toBeDefined();
    expect(node.status).toBe("quarantined");
    expect(node.phase).toBe("quarantined");
  });
});

// ─── Reversibility ────────────────────────────────────────────────────

describe("Reversibility", () => {
  test("every action is reversible", async () => {
    const initialPosture = (
      await request(app).get("/daedalus/governance/posture").expect(200)
    ).body;

    await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: "Test",
        scope: "NODE",
        effect: "ALLOW",
      })
      .expect(201);
    await request(app).delete("/daedalus/governance/overrides").expect(204);

    await request(app)
      .post("/daedalus/governance/votes")
      .send({
        being: { id: "operator", role: "OPERATOR", label: "Operator" },
        vote: "DENY",
        weight: 1.0,
      })
      .expect(201);
    await request(app).delete("/daedalus/governance/votes").expect(204);

    await request(app)
      .post("/daedalus/governance/drifts")
      .send({ severity: "HIGH", summary: "Critical drift" })
      .expect(201);
    await request(app).delete("/daedalus/governance/drifts").expect(204);

    const finalPosture = (
      await request(app).get("/daedalus/governance/posture").expect(200)
    ).body;

    expect(finalPosture.posture).toBe(initialPosture.posture);
    expect(finalPosture.posture).toBe("OPEN");
  });
});
