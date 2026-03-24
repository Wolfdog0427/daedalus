/**
 * Phase 2 — Being Store Audit
 *
 * Validates all being state flows: storage, seed correctness,
 * mutations, reads, event emission, patch semantics, and
 * snapshot consistency.
 */

import { daedalusStore } from "../orchestrator/daedalusStore";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import {
  BEING_ROLES,
  ROLE_DESCRIPTORS,
  createCanonicalOperator,
  createCanonicalGuardian,
  createCanonicalSentinel,
  BEING_POSTURE_ARCHETYPES,
  BEING_PRESENCE_MODES,
  BEING_ATTENTION_LEVELS,
} from "../../shared/daedalus/beingOntology";

// ─── Seed Correctness ────────────────────────────────────────────────

describe("Being seed correctness", () => {
  test("store seeds exactly operator and guardian-1", () => {
    const beings = daedalusStore.getBeingPresences();
    const ids = beings.map(b => b.id).sort();
    expect(ids).toEqual(["guardian-1", "operator"]);
  });

  test("operator seed has correct role defaults", () => {
    const op = daedalusStore.getBeingPresence("operator")!;
    expect(op.name).toBe("Operator");
    expect(op.posture).toBe("companion");
    expect(op.glow.level).toBe("high");
    expect(op.glow.intensity).toBeCloseTo(0.85, 1);
    expect(op.attention.level).toBe("focused");
    expect(op.influenceLevel).toBeCloseTo(0.9, 1);
    expect(op.presenceMode).toBe("active");
    expect(op.isGuiding).toBe(true);
    expect(op.isSpeaking).toBe(false);
    expect(op.continuity.healthy).toBe(true);
    expect(op.continuity.streak).toBe(12);
    expect(op.autopilot.enabled).toBe(false);
  });

  test("guardian-1 seed has correct role defaults", () => {
    const g = daedalusStore.getBeingPresence("guardian-1")!;
    expect(g.name).toBe("Guardian Alpha");
    expect(g.posture).toBe("sentinel");
    expect(g.glow.level).toBe("medium");
    expect(g.influenceLevel).toBeCloseTo(0.4, 1);
    expect(g.presenceMode).toBe("ambient");
    expect(g.continuity.healthy).toBe(true);
    expect(g.autopilot.enabled).toBe(true);
    expect(g.autopilot.scope).toBe("local");
  });

  test("seed beings have valid posture archetypes", () => {
    const beings = daedalusStore.getBeingPresences();
    for (const b of beings) {
      expect(BEING_POSTURE_ARCHETYPES).toContain(b.posture);
    }
  });

  test("seed beings have valid presence modes", () => {
    const beings = daedalusStore.getBeingPresences();
    for (const b of beings) {
      expect(BEING_PRESENCE_MODES).toContain(b.presenceMode);
    }
  });

  test("seed beings have valid attention levels", () => {
    const beings = daedalusStore.getBeingPresences();
    for (const b of beings) {
      expect(BEING_ATTENTION_LEVELS).toContain(b.attention.level);
    }
  });
});

// ─── Mutation Semantics ──────────────────────────────────────────────

describe("Being mutation semantics", () => {
  beforeEach(() => resetDaedalusEventBus());

  test("updateBeingPresence merges patch fields", () => {
    const before = daedalusStore.getBeingPresence("operator")!;
    daedalusStore.updateBeingPresence("operator", { isSpeaking: true });
    const after = daedalusStore.getBeingPresence("operator")!;

    expect(after.isSpeaking).toBe(true);
    expect(after.name).toBe(before.name);
    expect(after.posture).toBe(before.posture);
    expect(after.glow).toEqual(before.glow);
    expect(after.continuity.streak).toBe(before.continuity.streak);
  });

  test("updateBeingPresence refreshes updatedAt", () => {
    const before = daedalusStore.getBeingPresence("operator")!;
    const beforeTime = before.updatedAt;

    const delay = new Promise<void>(r => setTimeout(r, 5));
    return delay.then(() => {
      daedalusStore.updateBeingPresence("operator", { presenceMode: "dominant" });
      const after = daedalusStore.getBeingPresence("operator")!;
      expect(after.updatedAt).not.toBe(beforeTime);
    });
  });

  test("updateBeingPresence does not allow overriding id", () => {
    daedalusStore.updateBeingPresence("operator", { presenceMode: "idle" } as any);
    const after = daedalusStore.getBeingPresence("operator")!;
    expect(after.id).toBe("operator");
  });

  test("updateBeingPresence returns null for unknown being", () => {
    const result = daedalusStore.updateBeingPresence("phantom", { presenceMode: "idle" });
    expect(result).toBeNull();
  });

  test("nested glow object is replaced, not deep-merged", () => {
    daedalusStore.updateBeingPresence("operator", {
      glow: { level: "low", intensity: 0.1 },
    });
    const after = daedalusStore.getBeingPresence("operator")!;
    expect(after.glow.level).toBe("low");
    expect(after.glow.intensity).toBeCloseTo(0.1, 1);
  });

  test("nested continuity object is replaced, not deep-merged", () => {
    daedalusStore.updateBeingPresence("operator", {
      continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false },
    });
    const after = daedalusStore.getBeingPresence("operator")!;
    expect(after.continuity.healthy).toBe(false);
    expect(after.continuity.streak).toBe(0);
  });
});

// ─── Event Emission ──────────────────────────────────────────────────

describe("Being event emission", () => {
  test("BEING_PRESENCE_UPDATED fires on mutation with correct payload", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("guardian-1", {
      presenceMode: "active",
      influenceLevel: 0.7,
    });

    const beingEvents = events.filter(e => e.type === "BEING_PRESENCE_UPDATED");
    expect(beingEvents).toHaveLength(1);
    expect(beingEvents[0].beingId).toBe("guardian-1");
    expect(beingEvents[0].beingPresence?.presenceMode).toBe("active");
    expect(beingEvents[0].beingPresence?.influenceLevel).toBeCloseTo(0.7, 1);
    expect(beingEvents[0].timestamp).toBeDefined();
    expect(beingEvents[0].summary).toContain("Guardian Alpha");
  });

  test("no event fires for unknown being update", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("phantom", { presenceMode: "idle" });
    expect(events.filter(e => e.type === "BEING_PRESENCE_UPDATED")).toHaveLength(0);
  });

  test("multiple rapid updates emit multiple events", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("operator", { isSpeaking: true });
    daedalusStore.updateBeingPresence("operator", { isSpeaking: false });
    daedalusStore.updateBeingPresence("operator", { presenceMode: "idle" });

    const beingEvents = events.filter(e => e.type === "BEING_PRESENCE_UPDATED");
    expect(beingEvents).toHaveLength(3);
  });
});

// ─── Snapshot Consistency ────────────────────────────────────────────

describe("Being snapshot consistency", () => {
  test("getSnapshot returns beings array (coarse format)", () => {
    const snapshot = daedalusStore.getSnapshot();
    expect(Array.isArray(snapshot.beings)).toBe(true);
    expect(snapshot.beings.length).toBeGreaterThanOrEqual(1);
    expect(snapshot.beings[0]).toHaveProperty("id");
    expect(snapshot.beings[0]).toHaveProperty("label");
    expect(snapshot.beings[0]).toHaveProperty("nodes");
    expect(snapshot.beings[0]).toHaveProperty("dominantGlow");
    expect(snapshot.beings[0]).toHaveProperty("dominantRisk");
  });

  test("snapshot beings.nodes contains all node ids", () => {
    const snapshot = daedalusStore.getSnapshot();
    const nodeIds = snapshot.nodes.map(n => n.id).sort();
    for (const being of snapshot.beings) {
      const beingNodeIds = [...being.nodes].sort();
      expect(beingNodeIds).toEqual(nodeIds);
    }
  });

  test("getBeingPresences returns full BeingPresenceDetail objects", () => {
    const details = daedalusStore.getBeingPresences();
    for (const d of details) {
      expect(d).toHaveProperty("posture");
      expect(d).toHaveProperty("glow");
      expect(d).toHaveProperty("attention");
      expect(d).toHaveProperty("heartbeat");
      expect(d).toHaveProperty("influenceLevel");
      expect(d).toHaveProperty("presenceMode");
      expect(d).toHaveProperty("continuity");
      expect(d).toHaveProperty("autopilot");
      expect(d).toHaveProperty("updatedAt");
    }
  });
});

// ─── Ontology Factory Consistency ────────────────────────────────────

describe("Ontology factory functions produce valid beings", () => {
  test("createCanonicalOperator matches seed", () => {
    const op = createCanonicalOperator();
    expect(op.id).toBe("operator");
    expect(op.posture).toBe("companion");
    expect(op.influenceLevel).toBe(ROLE_DESCRIPTORS.OPERATOR.defaultInfluence);
    expect(op.presenceMode).toBe(ROLE_DESCRIPTORS.OPERATOR.defaultPresenceMode);
    expect(op.continuity.healthy).toBe(true);
  });

  test("createCanonicalGuardian produces sentinel posture", () => {
    const g = createCanonicalGuardian("g-test", "Test Guardian");
    expect(g.id).toBe("g-test");
    expect(g.posture).toBe("sentinel");
    expect(g.influenceLevel).toBe(ROLE_DESCRIPTORS.GUARDIAN.defaultInfluence);
    expect(g.presenceMode).toBe("ambient");
  });

  test("createCanonicalSentinel produces observer posture", () => {
    const s = createCanonicalSentinel("s-test", "Test Sentinel");
    expect(s.id).toBe("s-test");
    expect(s.posture).toBe("observer");
    expect(s.influenceLevel).toBe(ROLE_DESCRIPTORS.SENTINEL.defaultInfluence);
  });

  test("all roles are covered by descriptors", () => {
    for (const role of BEING_ROLES) {
      expect(ROLE_DESCRIPTORS[role]).toBeDefined();
      expect(ROLE_DESCRIPTORS[role].role).toBe(role);
    }
  });
});
