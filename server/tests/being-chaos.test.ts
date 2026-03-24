/**
 * Phase 6 — Being Chaos & Load Audit
 *
 * Validates: beings under rapid mutation, drift storms,
 * governance override cascades, simultaneous vote flips,
 * and high-throughput presence updates.
 */

import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import { computeExpressiveField } from "../../shared/daedalus/expressiveFieldEngine";
import { narrateContinuity } from "../../shared/daedalus/continuityNarrator";
import type { BeingPresenceDetail, BeingVote, DaedalusPosture } from "../../shared/daedalus/contracts";
import {
  createCanonicalOperator,
  createCanonicalGuardian,
  BEING_POSTURE_ARCHETYPES,
  BEING_PRESENCE_MODES,
} from "../../shared/daedalus/beingOntology";

function mkBeing(id: string, overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id,
    name: `Being ${id}`,
    posture: "companion",
    glow: { level: "medium", intensity: 0.5 },
    attention: { level: "aware" },
    heartbeat: Date.now(),
    influenceLevel: 0.5,
    presenceMode: "active",
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

// ─── Rapid Mutation Stress ───────────────────────────────────────────

describe("Being rapid mutation stress", () => {
  test("100 rapid updates to same being produce 100 events", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    for (let i = 0; i < 100; i++) {
      daedalusStore.updateBeingPresence("operator", {
        influenceLevel: Math.random(),
        presenceMode: BEING_PRESENCE_MODES[i % BEING_PRESENCE_MODES.length],
      });
    }

    const beingEvents = events.filter(e => e.type === "BEING_PRESENCE_UPDATED");
    expect(beingEvents).toHaveLength(100);
  });

  test("rapid posture oscillation settles on last value", () => {
    const postures: DaedalusPosture[] = ["sentinel", "companion", "observer", "dormant"];
    for (let i = 0; i < 50; i++) {
      daedalusStore.updateBeingPresence("operator", {
        posture: postures[i % postures.length],
      });
    }
    const final = daedalusStore.getBeingPresence("operator")!;
    expect(final.posture).toBe(postures[49 % postures.length]);
  });

  test("rapid glow intensity changes preserve level", () => {
    for (let i = 0; i < 50; i++) {
      daedalusStore.updateBeingPresence("operator", {
        glow: { level: "high", intensity: Math.random() },
      });
    }
    const final = daedalusStore.getBeingPresence("operator")!;
    expect(final.glow.level).toBe("high");
    expect(typeof final.glow.intensity).toBe("number");
  });
});

// ─── Drift Storm ─────────────────────────────────────────────────────

describe("Being drift storm", () => {
  test("rapid healthy → unhealthy → healthy oscillation produces correct signals", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    let prevHealth: Record<string, boolean> = {};

    for (let cycle = 0; cycle < 20; cycle++) {
      const healthy = cycle % 2 === 0;
      beings["op"] = mkBeing("op", {
        continuity: { streak: cycle, lastCheckIn: new Date().toISOString(), healthy },
      });

      const signals = narrateContinuity(beings, prevHealth);
      if (cycle > 0 && healthy && !prevHealth["op"]) {
        expect(signals.find(s => s.kind === "drift-recovery")).toBeDefined();
      }

      prevHealth = { op: healthy };
    }
  });

  test("many beings with mixed health produce correct stability", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (let i = 0; i < 50; i++) {
      beings[`b${i}`] = mkBeing(`b${i}`, {
        continuity: {
          streak: i,
          lastCheckIn: new Date().toISOString(),
          healthy: i % 3 !== 0,
        },
      });
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const totalBeings = 50;
    const unhealthyCount = Math.floor(50 / 3) + 1;
    const healthyCount = totalBeings - unhealthyCount;
    const expectedStability = healthyCount / totalBeings;

    expect(field.stability).toBeCloseTo(expectedStability, 1);
  });

  test("all beings simultaneously go unhealthy → stability = 0", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (let i = 0; i < 10; i++) {
      beings[`b${i}`] = mkBeing(`b${i}`, {
        continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false },
      });
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);
    expect(field.stability).toBe(0);
  });
});

// ─── Governance Override Cascade ─────────────────────────────────────

describe("Governance override cascade under stress", () => {
  test("50 rapid overrides are all recorded", () => {
    resetDaedalusEventBus();
    const service = new GovernanceService();

    for (let i = 0; i < 50; i++) {
      service.applyOverride({
        createdBy: { id: `being-${i}`, role: "SENTINEL", label: `Sentinel ${i}` },
        reason: `Override #${i}`,
        scope: "NODE",
        targetId: `node-${i}`,
        effect: "ALLOW",
      });
    }

    expect(service.listOverrides()).toHaveLength(50);
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  test("global DENY in middle of cascade takes effect", () => {
    resetDaedalusEventBus();
    const service = new GovernanceService();

    for (let i = 0; i < 25; i++) {
      service.applyOverride({
        createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
        reason: `Override #${i}`,
        scope: "NODE",
        targetId: `n-${i}`,
        effect: "ALLOW",
      });
    }

    service.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
      reason: "Emergency lockdown",
      scope: "GLOBAL",
      effect: "DENY",
    });

    for (let i = 25; i < 50; i++) {
      service.applyOverride({
        createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
        reason: `Override #${i}`,
        scope: "NODE",
        targetId: `n-${i}`,
        effect: "ALLOW",
      });
    }

    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });
});

// ─── Vote Flipping Storm ─────────────────────────────────────────────

describe("Vote flipping storm", () => {
  test("rapid vote changes settle on correct posture", () => {
    resetDaedalusEventBus();
    const service = new GovernanceService();

    const votes: Array<"ALLOW" | "DENY" | "ESCALATE"> = ["ALLOW", "DENY", "ESCALATE"];
    for (let i = 0; i < 100; i++) {
      service.castVote({
        being: { id: "op", role: "OPERATOR", label: "Operator" },
        vote: votes[i % 3],
        weight: 1.0,
      });
    }

    const lastVote = votes[99 % 3];
    const posture = service.getPostureSnapshot().posture;

    if (lastVote === "DENY") {
      expect(posture).toBe("LOCKDOWN");
    } else if (lastVote === "ESCALATE") {
      expect(posture).toBe("GUARDED");
    } else {
      expect(posture).toBe("ATTENTIVE");
    }

    expect(service.listVotes()).toHaveLength(1);
  });

  test("multiple beings voting simultaneously produces valid posture", () => {
    resetDaedalusEventBus();
    const service = new GovernanceService();

    for (let i = 0; i < 20; i++) {
      service.castVote({
        being: { id: `being-${i}`, role: i < 10 ? "GUARDIAN" : "SENTINEL", label: `Being ${i}` },
        vote: i % 2 === 0 ? "ALLOW" : "DENY",
        weight: 0.5 + Math.random() * 0.5,
      });
    }

    const posture = service.getPostureSnapshot().posture;
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(posture);
    expect(service.listVotes()).toHaveLength(20);
  });
});

// ─── High-Throughput Behavioral Field ────────────────────────────────

describe("High-throughput behavioral field computation", () => {
  test("100 beings produce valid behavioral field", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (let i = 0; i < 100; i++) {
      beings[`b${i}`] = mkBeing(`b${i}`, {
        influenceLevel: 0.1 + Math.random() * 0.9,
        presenceMode: BEING_PRESENCE_MODES[i % BEING_PRESENCE_MODES.length],
        isSpeaking: i === 0,
        isGuiding: i === 1,
      });
    }

    const behavioral = computeBehavioralField(beings);
    expect(behavioral.signals).toHaveLength(100);
    expect(behavioral.dominantBeingId).toBeDefined();

    const totalWeight = behavioral.signals.reduce(
      (sum, s) => sum + s.influenceWeight, 0,
    );
    expect(totalWeight).toBeCloseTo(1.0, 1);
  });

  test("100 beings produce valid expressive field", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (let i = 0; i < 100; i++) {
      beings[`b${i}`] = mkBeing(`b${i}`, {
        influenceLevel: Math.random(),
        posture: BEING_POSTURE_ARCHETYPES[i % BEING_POSTURE_ARCHETYPES.length],
      });
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(BEING_POSTURE_ARCHETYPES).toContain(field.posture);
    expect(field.stability).toBeGreaterThanOrEqual(0);
    expect(field.stability).toBeLessThanOrEqual(1);
    expect(field.arousal).toBeGreaterThanOrEqual(0);
    expect(field.focus).toBeGreaterThanOrEqual(0);
  });

  test("continuity narrator handles 100 beings without error", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (let i = 0; i < 100; i++) {
      beings[`b${i}`] = mkBeing(`b${i}`, {
        continuity: {
          streak: Math.floor(Math.random() * 50),
          lastCheckIn: new Date().toISOString(),
          healthy: Math.random() > 0.2,
        },
      });
    }

    const signals = narrateContinuity(beings);
    expect(Array.isArray(signals)).toBe(true);

    const anchor = signals.find(s => s.kind === "anchor");
    if (anchor) {
      expect(beings[anchor.beingId]).toBeDefined();
    }
  });
});
