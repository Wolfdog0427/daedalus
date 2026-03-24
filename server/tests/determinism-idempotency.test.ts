import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload, MirrorEvent } from "../orchestrator/mirror";
import {
  DaedalusEventBus,
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { daedalusStore } from "../orchestrator/daedalusStore";
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

const OP_BEING = { id: "op", role: "OPERATOR" as const, label: "Operator" };

// ─── DETERMINISM ────────────────────────────────────────────────────

describe("DETERMINISM", () => {
  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
  });

  test("same inputs produce same posture", () => {
    const svc1 = new GovernanceService();
    const svc2 = new GovernanceService();

    svc1.applyOverride({ createdBy: OP_BEING, reason: "test", scope: "NODE", targetId: "n1", effect: "ALLOW" });
    svc1.recordDrift({ severity: "MEDIUM", summary: "drift" });

    svc2.applyOverride({ createdBy: OP_BEING, reason: "test", scope: "NODE", targetId: "n1", effect: "ALLOW" });
    svc2.recordDrift({ severity: "MEDIUM", summary: "drift" });

    const snap1 = svc1.getPostureSnapshot();
    const snap2 = svc2.getPostureSnapshot();
    expect(snap1.posture).toBe(snap2.posture);
    expect(snap1.reason).toBe(snap2.reason);
  });

  test("same join payloads produce same mirror state", () => {
    const reg1 = new NodeMirrorRegistry();
    const reg2 = new NodeMirrorRegistry();

    reg1.handleJoin(mkJoin("n1"));
    reg2.handleJoin(mkJoin("n1"));

    const m1 = reg1.getMirror("n1")!;
    const m2 = reg2.getMirror("n1")!;

    expect(m1.id).toBe(m2.id);
    expect(m1.name).toBe(m2.name);
    expect(m1.lifecycle.phase).toBe(m2.lifecycle.phase);
    expect(m1.status).toBe(m2.status);
    expect(m1.capabilities.entries).toEqual(m2.capabilities.entries);
  });

  test("behavioral field is deterministic for same beings", () => {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;

    const field1 = computeBehavioralField(beingMap);
    const field2 = computeBehavioralField(beingMap);

    expect(field1.dominantBeingId).toBe(field2.dominantBeingId);
    const strip = (signals: any[]) =>
      signals.map(({ updatedAt, ...rest }) => rest);
    expect(strip(field1.signals)).toEqual(strip(field2.signals));
  });
});

// ─── IDEMPOTENCY ────────────────────────────────────────────────────

describe("IDEMPOTENCY", () => {
  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
  });

  test("double join: active node rejects re-join (phase guard), detach+rejoin works", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoin("node-1"));
    expect(() => reg.handleJoin(mkJoin("node-1"))).toThrow("Invalid phase transition");
    reg.handleDetach("node-1");
    reg.handleJoin(mkJoin("node-1"));
    expect(reg.getCount()).toBe(1);
    expect(reg.getMirror("node-1")).toBeDefined();
  });

  test("double heartbeat is safe", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoin("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));
    expect(reg.getMirror("node-1")!.lifecycle.heartbeatCount).toBe(2);
  });

  test("double override removal: first succeeds, second 404", () => {
    const svc = new GovernanceService();
    const o = svc.applyOverride({
      createdBy: OP_BEING,
      reason: "test",
      scope: "NODE",
      targetId: "n1",
      effect: "ALLOW",
    });
    expect(svc.removeOverride(o.id)).toBe(true);
    expect(svc.removeOverride(o.id)).toBe(false);
  });

  test("double vote from same being: replaces, doesn't duplicate", () => {
    const svc = new GovernanceService();
    svc.castVote({ being: { id: "b1", role: "GUARDIAN", label: "G1" }, vote: "ALLOW", weight: 0.5 });
    svc.castVote({ being: { id: "b1", role: "GUARDIAN", label: "G1" }, vote: "DENY", weight: 0.8 });
    const votes = svc.listVotes().filter((v) => v.being.id === "b1");
    expect(votes).toHaveLength(1);
    expect(votes[0].vote).toBe("DENY");
  });

  test("double quarantine: no-op second time", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe((e) => events.push(e));

    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));

    const beforeQuarantine = events.length;
    reg.handleQuarantine("node-1", "first");
    const afterFirst = events.length;
    reg.handleQuarantine("node-1", "second");
    const afterSecond = events.length;

    expect(reg.getMirror("node-1")!.lifecycle.phase).toBe("quarantined");
    const quarantineEventsFirst = afterFirst - beforeQuarantine;
    const quarantineEventsSecond = afterSecond - afterFirst;
    expect(quarantineEventsFirst).toBeGreaterThan(0);
    expect(quarantineEventsSecond).toBe(0);
  });

  test("clear on empty: no crash", () => {
    const svc = new GovernanceService();
    expect(() => svc.clearOverrides()).not.toThrow();
    expect(() => svc.clearVotes()).not.toThrow();
    expect(() => svc.clearDrifts()).not.toThrow();
  });
});

// ─── ORDERING ───────────────────────────────────────────────────────

describe("ORDERING", () => {
  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
  });

  test("events arrive in causal order", () => {
    const bus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));
    reg.handleError("node-1", "boom");
    reg.configureSafety({ errorQuarantineThreshold: 1 });
    reg.handleError("node-1", "boom again");

    const types = received.map((e) => e.type);
    const joinIdx = types.indexOf("MIRROR_NODE_JOINED");
    const hbIdx = types.indexOf("MIRROR_NODE_HEARTBEAT");
    const errIdx = types.indexOf("MIRROR_NODE_ERROR");

    expect(joinIdx).toBeLessThan(hbIdx);
    expect(hbIdx).toBeLessThan(errIdx);
  });

  test("posture changes only emit when actually changed", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const postureEvents: DaedalusEventPayload[] = [];
    bus.subscribe((e) => {
      if (e.type === "POSTURE_CHANGED") postureEvents.push(e);
    });

    const svc = new GovernanceService();

    svc.recordDrift({ severity: "MEDIUM", summary: "drift 1" });
    expect(postureEvents).toHaveLength(1);
    expect(postureEvents[0].posture).toBe("ATTENTIVE");

    svc.recordDrift({ severity: "MEDIUM", summary: "drift 2" });
    expect(postureEvents).toHaveLength(1);

    svc.clearDrifts();
    expect(postureEvents).toHaveLength(2);
    expect(postureEvents[1].posture).toBe("OPEN");
  });
});

// ─── BOUNDARY CONDITIONS ────────────────────────────────────────────

describe("BOUNDARY CONDITIONS", () => {
  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
  });

  test("errorCount at exactly threshold: triggers quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoin("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));

    reg.handleError("node-1", "err 1");
    reg.handleError("node-1", "err 2");
    reg.handleError("node-1", "err 3");

    expect(reg.getMirror("node-1")!.lifecycle.phase).toBe("quarantined");
  });

  test("errorCount at threshold-1: no quarantine", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoin("node-1"));
    reg.handleHeartbeat(mkHeartbeat("node-1"));

    reg.handleError("node-1", "err 1");
    reg.handleError("node-1", "err 2");

    expect(reg.getMirror("node-1")!.lifecycle.phase).not.toBe("quarantined");
  });

  test("vote weight at 0: accepted, doesn't influence", () => {
    const svc = new GovernanceService();
    svc.castVote({ being: { id: "b1", role: "GUARDIAN", label: "G1" }, vote: "DENY", weight: 0 });
    expect(svc.listVotes()).toHaveLength(1);
    expect(svc.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  test("vote weight at 1: maximum influence", () => {
    const svc = new GovernanceService();
    svc.castVote({ being: { id: "b1", role: "GUARDIAN", label: "G1" }, vote: "DENY", weight: 1 });
    expect(svc.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("stale sweep at exactly staleHeartbeatMs: not stale", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 30000 });
    reg.handleJoin(mkJoin("node-1"));

    const mirror = reg.getMirror("node-1")!;
    const hbTime = Date.now();
    reg.handleHeartbeat({ nodeId: "node-1", timestamp: new Date(hbTime).toISOString(), status: "alive" });

    const staleIds = reg.sweepStaleHeartbeats(hbTime + 30000);
    expect(staleIds).not.toContain("node-1");
  });

  test("stale sweep at staleHeartbeatMs + 1: stale", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 30000 });
    reg.handleJoin(mkJoin("node-1"));

    const hbTime = Date.now();
    reg.handleHeartbeat({ nodeId: "node-1", timestamp: new Date(hbTime).toISOString(), status: "alive" });

    const staleIds = reg.sweepStaleHeartbeats(hbTime + 30001);
    expect(staleIds).toContain("node-1");
  });

  test("being continuity streak = 0: still valid, not negative", () => {
    const updated = daedalusStore.updateBeingPresence("operator", {
      continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
    });
    expect(updated).not.toBeNull();
    expect(updated!.continuity.streak).toBe(0);
    expect(updated!.continuity.streak).toBeGreaterThanOrEqual(0);
  });

  test("influence level at boundaries 0.0 and 1.0: valid", () => {
    const low = daedalusStore.updateBeingPresence("operator", { influenceLevel: 0.0 });
    expect(low).not.toBeNull();
    expect(low!.influenceLevel).toBe(0.0);

    const high = daedalusStore.updateBeingPresence("operator", { influenceLevel: 1.0 });
    expect(high).not.toBeNull();
    expect(high!.influenceLevel).toBe(1.0);
  });
});
