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
  computeCapabilityDeltas,
  negotiateCapabilities,
  validateCapabilities,
  processCapSync,
  computeExpressiveDeltas,
  deriveGlowFromPhase,
  derivePostureFromPhase,
  processExpressiveSync,
  refreshExpressiveFromPhase,
  IDLE_EXPRESSIVE,
  IDLE_LIFECYCLE,
} from "../orchestrator/mirror";
import type {
  NodeMirror,
  NodeJoinPayload,
  NodeHeartbeatPayload,
  ExpressiveState,
  CockpitNodeView,
} from "../orchestrator/mirror";

function mkProfile(id = "n1") {
  return { id, name: id, kind: "mobile" as const, model: "S26", os: "android", osVersion: "15", operatorId: "op1" };
}

function mkJoinPayload(id = "n1"): NodeJoinPayload {
  return {
    nodeId: id,
    name: "Test Node",
    profile: mkProfile(id),
    capabilities: [
      { name: "vision", value: "enabled", enabled: true },
      { name: "audio", value: "disabled", enabled: false },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function mkHeartbeat(id = "n1", status: "alive" | "degraded" = "alive"): NodeHeartbeatPayload {
  return { nodeId: id, timestamp: new Date().toISOString(), status };
}

// ─── Lifecycle ───────────────────────────────────────────────────────

describe("NodeMirror.lifecycle", () => {
  test("createFreshMirror has correct initial state", () => {
    const mirror = createFreshMirror("n1");
    expect(mirror.id).toBe("n1");
    expect(mirror.status).toBe("unknown");
    expect(mirror.lifecycle.phase).toBe("discovered");
  });

  test("processJoin transitions through all phases to active", () => {
    const mirror = createFreshMirror("n1");
    const joined = processJoin(mirror, mkJoinPayload());
    expect(joined.lifecycle.phase).toBe("active");
    expect(joined.status).toBe("trusted");
    expect(joined.name).toBe("Test Node");
    expect(joined.capabilities.entries).toHaveLength(2);
  });

  test("processHeartbeat updates count and timestamp", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const hb = processHeartbeat(mirror, mkHeartbeat());
    expect(hb.lifecycle.heartbeatCount).toBe(1);
    expect(hb.lifecycle.lastHeartbeat).not.toBeNull();
  });

  test("degraded heartbeat transitions active to degraded", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const degraded = processHeartbeat(mirror, mkHeartbeat("n1", "degraded"));
    expect(degraded.lifecycle.phase).toBe("degraded");
  });

  test("alive heartbeat recovers degraded to active", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const degraded = processHeartbeat(mirror, mkHeartbeat("n1", "degraded"));
    const recovered = processHeartbeat(degraded, mkHeartbeat("n1", "alive"));
    expect(recovered.lifecycle.phase).toBe("active");
  });

  test("processQuarantine sets quarantined", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const q = processQuarantine(mirror);
    expect(q.lifecycle.phase).toBe("quarantined");
    expect(q.status).toBe("quarantined");
    expect(q.risk).toBe("high");
  });

  test("processDetach sets detached", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const q = processQuarantine(mirror);
    const d = processDetach(q);
    expect(d.lifecycle.phase).toBe("detached");
  });

  test("processError increments error count", () => {
    const mirror = createFreshMirror("n1");
    const errored = processError(mirror, "test error");
    expect(errored.lifecycle.errorCount).toBe(1);
    expect(errored.lifecycle.lastError).toBe("test error");
  });

  test("canTransitionPhase validates allowed transitions", () => {
    expect(canTransitionPhase("discovered", "joining")).toBe(true);
    expect(canTransitionPhase("discovered", "active")).toBe(false);
    expect(canTransitionPhase("active", "degraded")).toBe(true);
    expect(canTransitionPhase("detached", "active")).toBe(false);
  });

  test("phaseToStatus maps correctly", () => {
    expect(phaseToStatus("active")).toBe("trusted");
    expect(phaseToStatus("quarantined")).toBe("quarantined");
    expect(phaseToStatus("detached")).toBe("unknown");
    expect(phaseToStatus("joining")).toBe("pending");
  });
});

// ─── Capabilities ────────────────────────────────────────────────────

describe("NodeMirror.capabilities", () => {
  test("computeCapabilityDeltas detects additions", () => {
    const deltas = computeCapabilityDeltas(
      { entries: [] },
      [{ name: "a", value: "enabled", enabled: true }],
    );
    expect(deltas).toHaveLength(1);
    expect(deltas[0].from).toBeNull();
    expect(deltas[0].to.enabled).toBe(true);
  });

  test("computeCapabilityDeltas detects changes", () => {
    const deltas = computeCapabilityDeltas(
      { entries: [{ name: "a", value: "enabled", enabled: true }] },
      [{ name: "a", value: "disabled", enabled: false }],
    );
    expect(deltas).toHaveLength(1);
    expect(deltas[0].from!.enabled).toBe(true);
    expect(deltas[0].to.enabled).toBe(false);
  });

  test("computeCapabilityDeltas detects removals", () => {
    const deltas = computeCapabilityDeltas(
      { entries: [{ name: "a", value: "enabled", enabled: true }] },
      [],
    );
    expect(deltas).toHaveLength(1);
    expect(deltas[0].to.value).toBe("removed");
  });

  test("negotiateCapabilities intersects", () => {
    const local = [{ name: "a", value: "enabled", enabled: true }, { name: "b", value: "enabled", enabled: true }];
    const remote = [{ name: "b", value: "enabled", enabled: true }, { name: "c", value: "enabled", enabled: true }];
    const result = negotiateCapabilities(local, remote);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("b");
    expect(result[0].enabled).toBe(true);
  });

  test("validateCapabilities catches duplicates", () => {
    const errors = validateCapabilities([
      { name: "a", value: "", enabled: true },
      { name: "a", value: "", enabled: false },
    ]);
    expect(errors.length).toBeGreaterThan(0);
  });

  test("processCapSync updates mirror capabilities", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const result = processCapSync(mirror, {
      nodeId: "n1",
      capabilities: [{ name: "newcap", value: "enabled", enabled: true }],
      timestamp: new Date().toISOString(),
    });
    expect(result.mirror.capabilities.entries).toHaveLength(1);
    expect(result.mirror.capabilities.entries[0].name).toBe("newcap");
    expect(result.deltas.length).toBeGreaterThan(0);
  });
});

// ─── Expressive ──────────────────────────────────────────────────────

describe("NodeMirror.expressive", () => {
  test("computeExpressiveDeltas detects glow changes", () => {
    const from: ExpressiveState = { ...IDLE_EXPRESSIVE };
    const to: ExpressiveState = { ...IDLE_EXPRESSIVE, glow: { level: "high", intensity: 0.9 } };
    const deltas = computeExpressiveDeltas(from, to);
    expect(deltas).toHaveLength(1);
    expect(deltas[0].field).toBe("glow");
  });

  test("computeExpressiveDeltas detects posture changes", () => {
    const from: ExpressiveState = { ...IDLE_EXPRESSIVE };
    const to: ExpressiveState = { ...IDLE_EXPRESSIVE, posture: "companion" };
    const deltas = computeExpressiveDeltas(from, to);
    expect(deltas.find(d => d.field === "posture")).toBeDefined();
  });

  test("deriveGlowFromPhase active → high", () => {
    const glow = deriveGlowFromPhase("active", { level: "medium", intensity: 0.5 });
    expect(glow.level).toBe("high");
    expect(glow.intensity).toBeGreaterThanOrEqual(0.7);
  });

  test("deriveGlowFromPhase degraded → low", () => {
    const glow = deriveGlowFromPhase("degraded", { level: "high", intensity: 0.9 });
    expect(glow.level).toBe("low");
  });

  test("deriveGlowFromPhase quarantined → none", () => {
    const glow = deriveGlowFromPhase("quarantined", { level: "high", intensity: 0.9 });
    expect(glow.level).toBe("none");
  });

  test("derivePostureFromPhase maps correctly", () => {
    expect(derivePostureFromPhase("active")).toBe("companion");
    expect(derivePostureFromPhase("degraded")).toBe("observer");
    expect(derivePostureFromPhase("quarantined")).toBe("dormant");
  });

  test("refreshExpressiveFromPhase applies glow+posture", () => {
    const mirror = processJoin(createFreshMirror("n1"), mkJoinPayload());
    const refreshed = refreshExpressiveFromPhase(mirror);
    expect(refreshed.expressive.posture).toBe("companion");
    expect(refreshed.expressive.glow.level).toBe("high");
  });
});

// ─── Registry ────────────────────────────────────────────────────────

describe("NodeMirrorRegistry", () => {
  test("handleJoin registers a mirror", () => {
    const reg = new NodeMirrorRegistry();
    const mirror = reg.handleJoin(mkJoinPayload("n1"));
    expect(mirror.lifecycle.phase).toBe("active");
    expect(reg.getCount()).toBe(1);
    expect(reg.getMirror("n1")).toBeDefined();
  });

  test("handleHeartbeat updates existing mirror", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    const updated = reg.handleHeartbeat(mkHeartbeat("n1"));
    expect(updated).not.toBeNull();
    expect(updated!.lifecycle.heartbeatCount).toBe(1);
  });

  test("handleHeartbeat returns null for unknown node", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.handleHeartbeat(mkHeartbeat("unknown"))).toBeNull();
  });

  test("handleQuarantine + handleDetach", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleQuarantine("n1");
    expect(reg.getMirror("n1")!.status).toBe("quarantined");
    reg.handleDetach("n1");
    expect(reg.getMirror("n1")).toBeUndefined();
    expect(reg.getCount()).toBe(0);
  });

  test("handleCapSync returns deltas", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    const deltas = reg.handleCapSync({
      nodeId: "n1",
      capabilities: [{ name: "x", value: "enabled", enabled: true }],
      timestamp: new Date().toISOString(),
    });
    expect(deltas.length).toBeGreaterThan(0);
  });

  test("handleExpressiveSync returns deltas", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    const newExpr: ExpressiveState = { ...IDLE_EXPRESSIVE, posture: "sentinel" };
    const deltas = reg.handleExpressiveSync({
      nodeId: "n1",
      expressive: newExpr,
      timestamp: new Date().toISOString(),
    });
    expect(deltas.find(d => d.field === "posture")).toBeDefined();
  });

  test("subscribe receives events", () => {
    const reg = new NodeMirrorRegistry();
    const events: any[] = [];
    reg.subscribe(e => events.push(e));
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));
    expect(events.length).toBeGreaterThanOrEqual(2);
    expect(events[0].type).toBe("NODE_JOINED");
    expect(events[1].type).toBe("NODE_HEARTBEAT");
  });

  test("getAllMirrors returns all", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("a"));
    reg.handleJoin(mkJoinPayload("b"));
    expect(reg.getAllMirrors()).toHaveLength(2);
  });
});

// ─── Cockpit projection ──────────────────────────────────────────────

describe("NodeMirrorRegistry.toCockpitView", () => {
  test("returns empty array when no nodes exist", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.toCockpitView()).toEqual([]);
  });

  test("projects a single joined node correctly", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));

    const views = reg.toCockpitView();
    expect(views).toHaveLength(1);

    const v = views[0];
    expect(v.id).toBe("n1");
    expect(v.name).toBe("Test Node");
    expect(v.status).toBe("trusted");
    expect(v.phase).toBe("active");
    expect(v.kind).toBe("mobile");
    expect(v.glow).toBe("high");
    expect(v.glowIntensity).toBeGreaterThan(0);
    expect(v.posture).toBe("companion");
    expect(v.capabilities).toEqual(["vision", "audio"]);
    expect(v.heartbeatCount).toBe(0);
    expect(v.errorCount).toBe(0);
  });

  test("reflects heartbeat count and timestamp after heartbeats", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1"));

    const v = reg.toCockpitView()[0];
    expect(v.heartbeatCount).toBe(2);
    expect(v.lastHeartbeatAt).not.toBeNull();
  });

  test("reflects degraded status and posture change", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleHeartbeat(mkHeartbeat("n1", "degraded"));

    const v = reg.toCockpitView()[0];
    expect(v.phase).toBe("degraded");
    expect(v.glow).toBe("low");
    expect(v.posture).toBe("observer");
  });

  test("reflects quarantined state", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleQuarantine("n1");

    const v = reg.toCockpitView()[0];
    expect(v.status).toBe("quarantined");
    expect(v.risk).toBe("high");
    expect(v.glow).toBe("none");
    expect(v.posture).toBe("dormant");
  });

  test("reflects error count", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleError("n1", "oops");
    reg.handleError("n1", "oops again");

    const v = reg.toCockpitView()[0];
    expect(v.errorCount).toBe(2);
  });

  test("projects multiple nodes independently", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("a"));
    reg.handleJoin(mkJoinPayload("b"));
    reg.handleQuarantine("b");

    const views = reg.toCockpitView();
    expect(views).toHaveLength(2);

    const a = views.find(v => v.id === "a")!;
    const b = views.find(v => v.id === "b")!;

    expect(a.status).toBe("trusted");
    expect(b.status).toBe("quarantined");
    expect(a.glow).not.toBe(b.glow);
  });

  test("capabilities update reflects in cockpit view", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));
    reg.handleCapSync({
      nodeId: "n1",
      capabilities: [
        { name: "x", value: "enabled", enabled: true },
        { name: "y", value: "enabled", enabled: true },
      ],
      timestamp: new Date().toISOString(),
    });

    const v = reg.toCockpitView()[0];
    expect(v.capabilities).toEqual(["x", "y"]);
  });

  test("continuity label reflects healthy state", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoinPayload("n1"));

    const v = reg.toCockpitView()[0];
    expect(typeof v.continuity).toBe("string");
    expect(v.continuity).toMatch(/healthy|degraded/);
  });
});
