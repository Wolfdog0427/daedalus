/**
 * Phase 5 — Cockpit–Being Integration Audit
 *
 * Validates: being presence API for cockpit, SSE event delivery,
 * being anchor display, being influence on node cards, and
 * behavioral/expressive field derivation from beings.
 */

import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import { computeExpressiveField } from "../../shared/daedalus/expressiveFieldEngine";
import { narrateContinuity } from "../../shared/daedalus/continuityNarrator";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

const app = createOrchestratorApp();

// ─── Being Presence API ──────────────────────────────────────────────

describe("Cockpit being presence endpoints", () => {
  test("GET /daedalus/beings/presence returns all seeded beings", async () => {
    const res = await request(app).get("/daedalus/beings/presence").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThanOrEqual(2);

    const ids = res.body.map((b: any) => b.id);
    expect(ids).toContain("operator");
    expect(ids).toContain("guardian-1");
  });

  test("each being has all cockpit-required fields", async () => {
    const res = await request(app).get("/daedalus/beings/presence").expect(200);

    for (const being of res.body) {
      expect(being).toHaveProperty("id");
      expect(being).toHaveProperty("name");
      expect(being).toHaveProperty("posture");
      expect(being).toHaveProperty("glow");
      expect(being.glow).toHaveProperty("level");
      expect(being.glow).toHaveProperty("intensity");
      expect(being).toHaveProperty("attention");
      expect(being.attention).toHaveProperty("level");
      expect(being).toHaveProperty("influenceLevel");
      expect(being).toHaveProperty("presenceMode");
      expect(being).toHaveProperty("continuity");
      expect(being.continuity).toHaveProperty("streak");
      expect(being.continuity).toHaveProperty("healthy");
      expect(being).toHaveProperty("updatedAt");
    }
  });

  test("single being endpoint returns correct being", async () => {
    const res = await request(app)
      .get("/daedalus/beings/operator/presence")
      .expect(200);
    expect(res.body.id).toBe("operator");
    expect(res.body.posture).toBe("companion");
  });

  test("unknown being returns 404", async () => {
    await request(app)
      .get("/daedalus/beings/phantom/presence")
      .expect(404);
  });
});

// ─── Being Update via Cockpit ────────────────────────────────────────

describe("Cockpit being updates", () => {
  test("PUT updates being and returns updated state", async () => {
    const res = await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ presenceMode: "dominant", isSpeaking: true })
      .expect(200);

    expect(res.body.presenceMode).toBe("dominant");
    expect(res.body.isSpeaking).toBe(true);
    expect(res.body.id).toBe("operator");
  });

  test("PUT preserves fields not in patch", async () => {
    const before = (
      await request(app).get("/daedalus/beings/operator/presence")
    ).body;

    await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ isGuiding: false })
      .expect(200);

    const after = (
      await request(app).get("/daedalus/beings/operator/presence")
    ).body;

    expect(after.isGuiding).toBe(false);
    expect(after.name).toBe(before.name);
    expect(after.posture).toBe(before.posture);
  });
});

// ─── SSE Event Delivery ──────────────────────────────────────────────

describe("Being SSE events for cockpit", () => {
  test("BEING_PRESENCE_UPDATED event fires on update", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("guardian-1", {
      presenceMode: "active",
    });

    const beingEvents = events.filter(e => e.type === "BEING_PRESENCE_UPDATED");
    expect(beingEvents).toHaveLength(1);
    expect(beingEvents[0].beingId).toBe("guardian-1");
    expect(beingEvents[0].beingPresence).toBeDefined();
    expect(beingEvents[0].beingPresence!.presenceMode).toBe("active");
  });

  test("event carries full being state for client merge", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("operator", { posture: "sentinel" });

    const ev = events.find(e => e.type === "BEING_PRESENCE_UPDATED")!;
    const being = ev.beingPresence!;
    expect(being.posture).toBe("sentinel");
    expect(being.id).toBe("operator");
    expect(being.glow).toBeDefined();
    expect(being.continuity).toBeDefined();
  });
});

// ─── Being Anchor Display ────────────────────────────────────────────

describe("Being anchor display derivation", () => {
  test("anchor being is identifiable from continuity signals", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    const allBeings = daedalusStore.getBeingPresences();
    for (const b of allBeings) {
      beings[b.id] = b;
    }

    const signals = narrateContinuity(beings);
    const anchorSignal = signals.find(s => s.kind === "anchor");

    if (allBeings.length > 1) {
      const maxStreak = Math.max(...allBeings.map(b => b.continuity.streak));
      if (maxStreak > 3) {
        expect(anchorSignal).toBeDefined();
        const anchorBeing = allBeings.find(
          b => b.continuity.streak === maxStreak,
        );
        expect(anchorSignal!.beingId).toBe(anchorBeing!.id);
      }
    }
  });
});

// ─── Being Influence on Expressive Field ─────────────────────────────

describe("Being influence flows for cockpit", () => {
  test("behavioral field computes from seeded beings", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) {
      beings[b.id] = b;
    }

    const behavioral = computeBehavioralField(beings);
    expect(behavioral.signals.length).toBeGreaterThanOrEqual(2);
    expect(behavioral.dominantBeingId).toBeDefined();
  });

  test("dominant being has highest influence weight", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) {
      beings[b.id] = b;
    }

    const behavioral = computeBehavioralField(beings);
    const dominant = behavioral.signals.find(
      s => s.beingId === behavioral.dominantBeingId,
    );
    for (const s of behavioral.signals) {
      expect(dominant!.influenceWeight).toBeGreaterThanOrEqual(s.influenceWeight);
    }
  });

  test("expressive field posture matches dominant being posture", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) {
      beings[b.id] = b;
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const dominantBeing = beings[behavioral.dominantBeingId!];
    expect(field.posture).toBe(dominantBeing.posture);
  });

  test("expressive field glow matches dominant being glow", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) {
      beings[b.id] = b;
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const dominantBeing = beings[behavioral.dominantBeingId!];
    expect(field.glow.level).toBe(dominantBeing.glow.level);
  });

  test("stability reflects health of all beings", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) {
      beings[b.id] = b;
    }

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const totalBeings = Object.keys(beings).length;
    const healthyBeings = Object.values(beings).filter(
      b => b.continuity.healthy,
    ).length;
    expect(field.stability).toBeCloseTo(healthyBeings / totalBeings, 1);
  });
});
