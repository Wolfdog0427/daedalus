import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, MirrorEvent } from "../orchestrator/mirror";
import { GovernanceService, governanceService } from "../orchestrator/governance/GovernanceService";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

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

// ─── Telemetry Completeness ─────────────────────────────────────────

describe("Telemetry Completeness", () => {
  let reg: NodeMirrorRegistry;
  let busEvents: DaedalusEventPayload[];
  let mirrorEvents: MirrorEvent[];

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    reg = getNodeMirrorRegistry();
    busEvents = [];
    mirrorEvents = [];
    getDaedalusEventBus().subscribe((e) => busEvents.push(e));
    reg.subscribe((e) => mirrorEvents.push(e));
  });

  test("node join emits MIRROR_NODE_JOINED event", () => {
    reg.handleJoin(mkJoin("tel-1"));

    const busHit = busEvents.find((e) => e.type === "MIRROR_NODE_JOINED");
    expect(busHit).toBeDefined();
    expect(busHit!.nodeId).toBe("tel-1");

    const mirrorHit = mirrorEvents.find((e) => e.type === "NODE_JOINED");
    expect(mirrorHit).toBeDefined();
    expect(mirrorHit!.nodeId).toBe("tel-1");
  });

  test("heartbeat emits MIRROR_NODE_HEARTBEAT event", () => {
    reg.handleJoin(mkJoin("tel-hb"));
    busEvents.length = 0;
    mirrorEvents.length = 0;

    reg.handleHeartbeat({ nodeId: "tel-hb", timestamp: new Date().toISOString(), status: "alive" });

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_HEARTBEAT")).toBe(true);
    expect(mirrorEvents.some((e) => e.type === "NODE_HEARTBEAT")).toBe(true);
  });

  test("quarantine emits MIRROR_NODE_QUARANTINED event", () => {
    reg.handleJoin(mkJoin("tel-q"));
    busEvents.length = 0;

    reg.handleQuarantine("tel-q", "test reason");

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_QUARANTINED")).toBe(true);
    expect(busEvents.find((e) => e.type === "MIRROR_NODE_QUARANTINED")!.nodeId).toBe("tel-q");
  });

  test("detach emits MIRROR_NODE_DETACHED event", () => {
    reg.handleJoin(mkJoin("tel-d"));
    reg.handleQuarantine("tel-d");
    busEvents.length = 0;

    reg.handleDetach("tel-d");

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_DETACHED")).toBe(true);
  });

  test("error emits MIRROR_NODE_ERROR event", () => {
    reg.handleJoin(mkJoin("tel-err"));
    busEvents.length = 0;

    reg.handleError("tel-err", "something broke");

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_ERROR")).toBe(true);
  });

  test("stale sweep emits MIRROR_NODE_STALE event", () => {
    reg.configureSafety({ staleHeartbeatMs: 1_000, errorQuarantineThreshold: 100 });
    reg.handleJoin(mkJoin("tel-stale"));
    reg.handleHeartbeat({ nodeId: "tel-stale", timestamp: new Date().toISOString(), status: "alive" });
    busEvents.length = 0;

    reg.sweepStaleHeartbeats(Date.now() + 10_000);

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_STALE")).toBe(true);
  });

  test("cap sync emits MIRROR_NODE_CAP_SYNCED event", () => {
    reg.handleJoin(mkJoin("tel-cap"));
    busEvents.length = 0;

    reg.handleCapSync({
      nodeId: "tel-cap",
      capabilities: [{ name: "vision", value: "enabled", enabled: true }],
      timestamp: new Date().toISOString(),
    });

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_CAP_SYNCED")).toBe(true);
  });

  test("expressive sync emits MIRROR_NODE_EXPRESSIVE_SYNCED event", () => {
    reg.handleJoin(mkJoin("tel-exp"));
    busEvents.length = 0;

    reg.handleExpressiveSync({
      nodeId: "tel-exp",
      expressive: { ...IDLE_EXPRESSIVE, posture: "sentinel" as const },
      timestamp: new Date().toISOString(),
    });

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_EXPRESSIVE_SYNCED")).toBe(true);
  });

  test("profile sync emits MIRROR_NODE_PROFILE_SYNCED event", () => {
    reg.handleJoin(mkJoin("tel-prof"));
    busEvents.length = 0;

    reg.handleProfileSync({
      nodeId: "tel-prof",
      profile: { id: "tel-prof", name: "Updated", kind: "desktop" as const, model: "X", os: "win", osVersion: "11", operatorId: "operator" },
      timestamp: new Date().toISOString(),
    });

    expect(busEvents.some((e) => e.type === "MIRROR_NODE_PROFILE_SYNCED")).toBe(true);
  });

  test("override create emits GOVERNANCE_OVERRIDE_APPLIED event", () => {
    const svc = new GovernanceService();
    svc.applyOverride(mkOverride("NODE", "DENY"));

    expect(busEvents.some((e) => e.type === "GOVERNANCE_OVERRIDE_APPLIED")).toBe(true);
  });

  test("drift record emits CONTINUITY_DRIFT_DETECTED event", () => {
    const svc = new GovernanceService();
    svc.recordDrift({ severity: "MEDIUM", summary: "test drift" });

    expect(busEvents.some((e) => e.type === "CONTINUITY_DRIFT_DETECTED")).toBe(true);
  });

  test("posture change emits POSTURE_CHANGED event", () => {
    const svc = new GovernanceService();
    svc.applyOverride(mkOverride("GLOBAL", "DENY"));

    const postureHit = busEvents.find((e) => e.type === "POSTURE_CHANGED");
    expect(postureHit).toBeDefined();
    expect(postureHit!.posture).toBe("LOCKDOWN");
  });

  test("vote cast emits GOVERNANCE_OVERRIDE_APPLIED event", () => {
    const svc = new GovernanceService();
    svc.castVote({
      being: { id: "voter-1", role: "GUARDIAN", label: "V1" },
      vote: "ALLOW",
      weight: 0.5,
    });

    const voteHit = busEvents.find(
      (e) => e.type === "GOVERNANCE_OVERRIDE_APPLIED" && e.beings != null,
    );
    expect(voteHit).toBeDefined();
  });

  test("being presence update emits BEING_PRESENCE_UPDATED event", () => {
    daedalusStore.updateBeingPresence("operator", { presenceMode: "active" });

    const hit = busEvents.find((e) => e.type === "BEING_PRESENCE_UPDATED");
    expect(hit).toBeDefined();
    expect(hit!.beingId).toBe("operator");
  });

  test("negotiation apply emits NEGOTIATION_COMPLETED event", async () => {
    reg.handleJoin(mkJoin("neg-node"));

    const app = createOrchestratorApp();
    const snapshotRes = await request(app).get("/daedalus/snapshot").expect(200);
    const node = snapshotRes.body.nodes.find(
      (n: any) => n.id === "neg-node" && n.capabilities.some((c: any) => c.enabled),
    );

    if (!node) return;

    const cap = node.capabilities.find((c: any) => c.enabled);
    busEvents.length = 0;

    await request(app)
      .post("/daedalus/negotiations/apply")
      .send({
        requestedBy: { id: "operator" },
        targetNodeId: node.id,
        capabilityName: cap.name,
        desiredEnabled: false,
      })
      .expect(200);

    const negHit = busEvents.find((e) => e.type === "NEGOTIATION_COMPLETED");
    expect(negHit).toBeDefined();
  });
});

// ─── Traceability ───────────────────────────────────────────────────

describe("Traceability", () => {
  test("full node lifecycle produces ordered events", () => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();

    const reg = getNodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 100 });

    const busEvents: DaedalusEventPayload[] = [];
    getDaedalusEventBus().subscribe((e) => busEvents.push(e));

    reg.handleJoin(mkJoin("lifecycle-1"));

    for (let i = 0; i < 3; i++) {
      reg.handleHeartbeat({ nodeId: "lifecycle-1", timestamp: new Date().toISOString(), status: "alive" });
    }

    for (let i = 0; i < 5; i++) {
      reg.handleError("lifecycle-1", `error-${i}`);
    }

    reg.handleQuarantine("lifecycle-1", "lifecycle test");
    reg.handleDetach("lifecycle-1");

    const nodeEvents = busEvents.filter((e) => e.nodeId === "lifecycle-1");

    const typeSequence = nodeEvents.map((e) => e.type);

    const joinIdx = typeSequence.indexOf("MIRROR_NODE_JOINED");
    const lastHeartbeatIdx = typeSequence.lastIndexOf("MIRROR_NODE_HEARTBEAT");
    const firstErrorIdx = typeSequence.indexOf("MIRROR_NODE_ERROR");
    const quarantineIdx = typeSequence.indexOf("MIRROR_NODE_QUARANTINED");
    const detachIdx = typeSequence.indexOf("MIRROR_NODE_DETACHED");

    expect(joinIdx).toBeGreaterThanOrEqual(0);
    expect(lastHeartbeatIdx).toBeGreaterThan(joinIdx);
    expect(firstErrorIdx).toBeGreaterThan(lastHeartbeatIdx);
    expect(quarantineIdx).toBeGreaterThan(firstErrorIdx);
    expect(detachIdx).toBeGreaterThan(quarantineIdx);

    const heartbeatEvents = nodeEvents.filter((e) => e.type === "MIRROR_NODE_HEARTBEAT");
    expect(heartbeatEvents).toHaveLength(3);

    const errorEvents = nodeEvents.filter((e) => e.type === "MIRROR_NODE_ERROR");
    expect(errorEvents).toHaveLength(5);

    const timestamps = nodeEvents.map((e) => new Date(e.timestamp).getTime());
    for (let i = 1; i < timestamps.length; i++) {
      expect(timestamps[i]).toBeGreaterThanOrEqual(timestamps[i - 1]);
    }
  });

  test("continuity anchor can be traced from being state", () => {
    const beings = daedalusStore.getBeingPresences();
    expect(beings.length).toBeGreaterThan(0);

    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;

    const behavioral = computeBehavioralField(beingMap);
    const anchorId = behavioral.dominantBeingId;

    if (anchorId) {
      const anchor = beings.find((b) => b.id === anchorId);
      expect(anchor).toBeDefined();

      const highestStreak = Math.max(...beings.map((b) => b.continuity.streak));
      expect(anchor!.continuity.streak).toBe(highestStreak);
    }
  });
});

// ─── Constitution Visibility (via HTTP) ─────────────────────────────

describe("Constitution Visibility (via HTTP)", () => {
  const app = createOrchestratorApp();

  test("GET /daedalus/constitution returns valid report", async () => {
    const res = await request(app).get("/daedalus/constitution").expect(200);

    expect(typeof res.body.allPassed).toBe("boolean");
    expect(Array.isArray(res.body.checks)).toBe(true);
    expect(res.body.checks.length).toBe(10);

    for (const check of res.body.checks) {
      expect(check.name).toBeDefined();
      expect(typeof check.passed).toBe("boolean");
    }
  });

  test("constitution report reflects real being state", async () => {
    await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ presenceMode: "dominant", influenceLevel: 0.9 })
      .expect(200);

    const res = await request(app).get("/daedalus/constitution").expect(200);

    const operatorCheck = res.body.checks.find(
      (c: any) => c.name === "operator-always-present",
    );
    expect(operatorCheck).toBeDefined();
    expect(operatorCheck.passed).toBe(true);
  });
});
