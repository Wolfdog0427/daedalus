/**
 * Governance & Safety Envelope — validates that the governance layer
 * enforces its rules: phase transitions locked, quarantine enforced,
 * error thresholds active, stale heartbeat detection, risk tier mapping.
 */

import {
  NodeMirrorRegistry,
  createFreshMirror,
  processJoin,
  processHeartbeat,
  processQuarantine,
  processDetach,
  processError,
  canTransitionPhase,
  phaseToStatus,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload } from "../orchestrator/mirror";

function mkProfile(id = "n1") {
  return { id, name: id, kind: "mobile" as const, model: "S26", os: "android", osVersion: "15", operatorId: "operator" };
}

function mkJoinPayload(id = "n1"): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: mkProfile(id),
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function mkHeartbeat(id = "n1", status: "alive" | "degraded" = "alive"): NodeHeartbeatPayload {
  return { nodeId: id, timestamp: new Date().toISOString(), status };
}

// ─── Phase Transitions (locked) ──────────────────────────────────────

describe("Phase transitions are locked", () => {
  test("discovered can only go to joining", () => {
    expect(canTransitionPhase("discovered", "joining")).toBe(true);
    expect(canTransitionPhase("discovered", "active")).toBe(false);
    expect(canTransitionPhase("discovered", "quarantined")).toBe(false);
    expect(canTransitionPhase("discovered", "detached")).toBe(false);
  });

  test("active can degrade, quarantine, or detach — nothing else", () => {
    expect(canTransitionPhase("active", "degraded")).toBe(true);
    expect(canTransitionPhase("active", "quarantined")).toBe(true);
    expect(canTransitionPhase("active", "detached")).toBe(true);
    expect(canTransitionPhase("active", "joining")).toBe(false);
    expect(canTransitionPhase("active", "discovered")).toBe(false);
  });

  test("degraded can recover to active, quarantine, or detach", () => {
    expect(canTransitionPhase("degraded", "active")).toBe(true);
    expect(canTransitionPhase("degraded", "quarantined")).toBe(true);
    expect(canTransitionPhase("degraded", "detached")).toBe(true);
    expect(canTransitionPhase("degraded", "joining")).toBe(false);
  });

  test("quarantined can only detach — no recovery", () => {
    expect(canTransitionPhase("quarantined", "detached")).toBe(true);
    expect(canTransitionPhase("quarantined", "active")).toBe(false);
    expect(canTransitionPhase("quarantined", "degraded")).toBe(false);
    expect(canTransitionPhase("quarantined", "joining")).toBe(false);
  });

  test("detached is terminal — no outgoing transitions", () => {
    expect(canTransitionPhase("detached", "active")).toBe(false);
    expect(canTransitionPhase("detached", "joining")).toBe(false);
    expect(canTransitionPhase("detached", "discovered")).toBe(false);
    expect(canTransitionPhase("detached", "quarantined")).toBe(false);
  });

  test("phaseToStatus maps correctly for governance visibility", () => {
    expect(phaseToStatus("discovered")).toBe("pending");
    expect(phaseToStatus("joining")).toBe("pending");
    expect(phaseToStatus("active")).toBe("trusted");
    expect(phaseToStatus("degraded")).toBe("pending");
    expect(phaseToStatus("quarantined")).toBe("quarantined");
    expect(phaseToStatus("detached")).toBe("unknown");
  });
});

// ─── Quarantine Rules ────────────────────────────────────────────────

describe("Quarantine rules", () => {
  test("quarantine sets risk to high", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const q = processQuarantine(mirror);
    expect(q.risk).toBe("high");
    expect(q.status).toBe("quarantined");
    expect(q.lifecycle.phase).toBe("quarantined");
  });

  test("quarantined node cannot return to active", () => {
    expect(canTransitionPhase("quarantined", "active")).toBe(false);
  });

  test("quarantined node can only be detached", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const q = processQuarantine(mirror);
    const d = processDetach(q);
    expect(d.lifecycle.phase).toBe("detached");
  });

  test("registry handleQuarantine is idempotent on already-quarantined", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleQuarantine("n1");
    reg.handleQuarantine("n1");
    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("quarantined");
  });
});

// ─── Error Threshold Auto-Quarantine ─────────────────────────────────

describe("Error threshold auto-quarantine", () => {
  test("errors below threshold do not trigger quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 5 });
    reg.handleJoin(mkJoinPayload("n1"));

    for (let i = 0; i < 4; i++) {
      reg.handleError("n1", `error ${i}`);
    }

    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("active");
    expect(reg.getMirror("n1")!.lifecycle.errorCount).toBe(4);
  });

  test("reaching error threshold triggers automatic quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoinPayload("n1"));

    const events: any[] = [];
    reg.subscribe(e => events.push(e));

    reg.handleError("n1", "err1");
    reg.handleError("n1", "err2");
    reg.handleError("n1", "err3");

    const mirror = reg.getMirror("n1")!;
    expect(mirror.lifecycle.phase).toBe("quarantined");
    expect(mirror.risk).toBe("high");
    expect(mirror.lifecycle.errorCount).toBe(3);

    const quarantineEvent = events.find(e => e.type === "NODE_QUARANTINED");
    expect(quarantineEvent).toBeDefined();
    expect(quarantineEvent.reason).toContain("exceeded threshold");
  });

  test("errors on already-quarantined node do not double-quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 2 });
    reg.handleJoin(mkJoinPayload("n1"));

    reg.handleError("n1", "err1");
    reg.handleError("n1", "err2");
    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("quarantined");

    reg.handleError("n1", "err3");
    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("quarantined");
    expect(reg.getMirror("n1")!.lifecycle.errorCount).toBe(3);
  });

  test("default threshold is 5", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.getSafety().errorQuarantineThreshold).toBe(5);
  });
});

// ─── Stale Heartbeat Detection ───────────────────────────────────────

describe("Stale heartbeat detection", () => {
  test("sweepStaleHeartbeats returns no stale nodes when all are fresh", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));

    const stale = reg.sweepStaleHeartbeats(Date.now());
    expect(stale).toEqual([]);
  });

  test("sweepStaleHeartbeats detects nodes past the threshold", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 10_000 });
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));

    const futureMs = Date.now() + 15_000;
    const stale = reg.sweepStaleHeartbeats(futureMs);
    expect(stale).toContain("n1");
  });

  test("sweepStaleHeartbeats increments error count on stale nodes", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 5_000, errorQuarantineThreshold: 100 });
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));

    const futureMs = Date.now() + 10_000;
    reg.sweepStaleHeartbeats(futureMs);
    expect(reg.getMirror("n1")!.lifecycle.errorCount).toBeGreaterThan(0);
  });

  test("repeated stale sweeps accumulate errors and eventually quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 1_000, errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));

    const base = Date.now();
    reg.sweepStaleHeartbeats(base + 2_000);
    reg.sweepStaleHeartbeats(base + 3_000);
    reg.sweepStaleHeartbeats(base + 4_000);

    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("quarantined");
  });

  test("sweepStaleHeartbeats ignores quarantined and detached nodes", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 1_000 });
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));
    reg.handleQuarantine("n1");

    const stale = reg.sweepStaleHeartbeats(Date.now() + 10_000);
    expect(stale).toEqual([]);
  });

  test("default stale threshold is 30 seconds", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.getSafety().staleHeartbeatMs).toBe(30_000);
  });
});

// ─── Recovery Logic ──────────────────────────────────────────────────

describe("Recovery logic", () => {
  test("degraded node recovers to active on alive heartbeat", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat({ ...mkHeartbeat("n1"), status: "degraded" });
    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("degraded");

    reg.handleHeartbeat({ ...mkHeartbeat("n1"), status: "alive" });
    expect(reg.getMirror("n1")!.lifecycle.phase).toBe("active");
  });

  test("heartbeat increments count even during degraded state", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat({ ...mkHeartbeat("n1"), status: "degraded" });
    reg.handleHeartbeat({ ...mkHeartbeat("n1"), status: "degraded" });
    expect(reg.getMirror("n1")!.lifecycle.heartbeatCount).toBe(2);
  });

  test("heartbeat for unknown node returns null (no crash)", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.handleHeartbeat(mkHeartbeat("ghost"))).toBeNull();
  });
});

// ─── Risk Tier Mapping ───────────────────────────────────────────────

describe("Risk tier mapping", () => {
  test("fresh mirror starts at medium risk", () => {
    const m = createFreshMirror("n1");
    expect(m.risk).toBe("medium");
  });

  test("quarantine escalates risk to high", () => {
    const m = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const q = processQuarantine(m);
    expect(q.risk).toBe("high");
  });

  test("join does not reset risk — preserves from processJoin", () => {
    const reg = new NodeMirrorRegistry();
    const mirror = reg.handleJoin(mkJoinPayload("n1"));
    expect(mirror.risk).toBe("medium");
  });
});

// ─── Governance Posture ──────────────────────────────────────────────

describe("Governance posture computation", () => {
  // These use the GovernanceService directly
  let service: any;

  beforeEach(async () => {
    const mod = await import("../orchestrator/governance/GovernanceService");
    service = new mod.GovernanceService();
  });

  test("initial posture is OPEN", () => {
    const snapshot = service.getPostureSnapshot();
    expect(snapshot.posture).toBe("OPEN");
  });

  test("global DENY override triggers LOCKDOWN", () => {
    service.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
      reason: "Emergency",
      scope: "GLOBAL",
      effect: "DENY",
    });
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("HIGH severity drift triggers GUARDED", () => {
    service.recordDrift({ severity: "HIGH", summary: "Identity drift detected" });
    expect(service.getPostureSnapshot().posture).toBe("GUARDED");
  });

  test("MEDIUM drift triggers ATTENTIVE", () => {
    service.recordDrift({ severity: "MEDIUM", summary: "Minor drift" });
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  test("any override without global deny triggers ATTENTIVE", () => {
    service.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
      reason: "Tuning",
      scope: "NODE",
      targetId: "n1",
      effect: "ALLOW",
    });
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });
});

// ─── Mirror Routes Exist ─────────────────────────────────────────────

describe("Mirror HTTP routes are wired", () => {
  let app: any;
  let request: any;

  beforeAll(async () => {
    const supertest = await import("supertest");
    const { createOrchestratorApp } = await import("../orchestrator/index");
    const { resetNodeMirrorRegistry } = await import("../orchestrator/mirror");
    resetNodeMirrorRegistry();
    app = createOrchestratorApp();
    request = supertest.default(app);
  });

  test("POST /daedalus/mirror/join registers a node", async () => {
    const res = await request.post("/daedalus/mirror/join").send(mkJoinPayload("route-test"));
    expect(res.status).toBe(201);
    expect(res.body.nodeId).toBe("route-test");
    expect(res.body.phase).toBe("active");
  });

  test("POST /daedalus/mirror/heartbeat updates a node", async () => {
    const res = await request.post("/daedalus/mirror/heartbeat").send(mkHeartbeat("route-test"));
    expect(res.status).toBe(200);
    expect(res.body.nodeId).toBe("route-test");
  });

  test("POST /daedalus/mirror/heartbeat returns 404 for unknown node", async () => {
    const res = await request.post("/daedalus/mirror/heartbeat").send(mkHeartbeat("ghost"));
    expect(res.status).toBe(404);
  });

  test("POST /daedalus/mirror/capabilities syncs capabilities", async () => {
    const res = await request.post("/daedalus/mirror/capabilities").send({
      nodeId: "route-test",
      capabilities: [{ name: "vision", value: "enabled", enabled: true }],
      timestamp: new Date().toISOString(),
    });
    expect(res.status).toBe(200);
    expect(res.body.deltaCount).toBeGreaterThan(0);
  });

  test("POST /daedalus/mirror/expressive syncs expressive state", async () => {
    const res = await request.post("/daedalus/mirror/expressive").send({
      nodeId: "route-test",
      expressive: { ...IDLE_EXPRESSIVE, posture: "sentinel" },
      timestamp: new Date().toISOString(),
    });
    expect(res.status).toBe(200);
  });

  test("POST /daedalus/mirror/quarantine quarantines a node", async () => {
    const res = await request.post("/daedalus/mirror/quarantine").send({ nodeId: "route-test" });
    expect(res.status).toBe(200);
    expect(res.body.quarantined).toBe(true);
  });

  test("POST /daedalus/mirror/join rejects missing nodeId", async () => {
    const res = await request.post("/daedalus/mirror/join").send({ name: "foo" });
    expect(res.status).toBe(400);
  });
});
