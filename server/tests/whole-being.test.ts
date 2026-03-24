/**
 * WHOLE-BEING AUDIT — The Final Test Before Activation
 *
 * This test validates Daedalus as a single, coherent, living system.
 * Every layer is exercised, every integration point verified, every
 * invariant confirmed. If this passes, Daedalus is ready.
 *
 * Layers tested:
 *  1. Identity         8. Events
 *  2. Beings           9. Persistence (cold start)
 *  3. Attention       10. Operator experience
 *  4. Continuity      11. Node fabric
 *  5. Capabilities    12. Orchestrator
 *  6. Expressive      13. Cockpit
 *  7. Governance      14. Whole-being coherence
 */

import supertest from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";

const TOKEN = "daedalus-dev-token";
function request(app: any) {
  const agent = supertest(app);
  const wrap = (method: "get" | "post" | "put" | "delete") => (url: string) =>
    (agent as any)[method](url).set("x-daedalus-token", TOKEN);
  return { get: wrap("get"), post: wrap("post"), put: wrap("put"), delete: wrap("delete") };
}
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  createFreshMirror,
  processJoin,
  processHeartbeat,
  processQuarantine,
  processDetach,
  canTransitionPhase,
  deriveGlowFromPhase,
  derivePostureFromPhase,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload } from "../orchestrator/mirror";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import { computeExpressiveField, EXPRESSIVE_DEFAULTS } from "../../shared/daedalus/expressiveFieldEngine";
import { narrateContinuity } from "../../shared/daedalus/continuityNarrator";
import {
  computeSystemContinuity,
  computeIdentityContinuity,
  deriveContinuityHealth,
} from "../../shared/daedalus/systemContinuityEngine";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import {
  DAEDALUS_IDENTITY,
  CANONICAL_OPERATOR_ID,
  CANONICAL_ANCHOR_BEING_ID,
} from "../../shared/daedalus/identity";
import { GLOW_PALETTE, glowLevelToHex } from "../../shared/daedalus/glowPalette";
import { ROLE_DESCRIPTORS, BEING_POSTURE_ARCHETYPES } from "../../shared/daedalus/beingOntology";
import type { BeingPresenceDetail, BeingVote } from "../../shared/daedalus/contracts";

const app = createOrchestratorApp();

function mkJoin(id: string): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: { id, name: id, kind: "mobile", model: "S26", os: "android", osVersion: "15", operatorId: CANONICAL_OPERATOR_ID },
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

// ═══════════════════════════════════════════════════════════════════════
// 1. IDENTITY LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("1. Identity", () => {
  test("Daedalus identity is canonical and frozen", () => {
    expect(DAEDALUS_IDENTITY.name).toBe("Daedalus");
    expect(DAEDALUS_IDENTITY.sigil).toBe("labyrinth");
    expect(DAEDALUS_IDENTITY.gates).toHaveLength(2);
    expect(DAEDALUS_IDENTITY.gates[0].name).toBe("Crown Gate");
    expect(DAEDALUS_IDENTITY.gates[1].name).toBe("Fabric Gate");
    expect(DAEDALUS_IDENTITY.operatorId).toBe("operator");
    expect(DAEDALUS_IDENTITY.anchorBeingId).toBe("operator");
    expect(Object.isFrozen(DAEDALUS_IDENTITY)).toBe(true);
  });

  test("glow palette covers all levels with valid colors", () => {
    for (const level of ["none", "low", "medium", "high"] as const) {
      const color = GLOW_PALETTE[level];
      expect(color.hex).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(color.shadow).toMatch(/^(#[0-9a-fA-F]{6,8}|transparent)$/);
      expect(typeof color.motionPattern).toBe("string");
    }
  });

  test("posture archetypes are complete and frozen", () => {
    expect(BEING_POSTURE_ARCHETYPES).toEqual(["sentinel", "companion", "observer", "dormant"]);
    expect(Object.isFrozen(BEING_POSTURE_ARCHETYPES)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 2. BEINGS LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("2. Beings", () => {
  test("store seeds operator and guardian with correct ontology", () => {
    const beings = daedalusStore.getBeingPresences();
    expect(beings.length).toBeGreaterThanOrEqual(2);

    const op = daedalusStore.getBeingPresence("operator")!;
    expect(op.posture).toBe("companion");
    expect(op.influenceLevel).toBeCloseTo(ROLE_DESCRIPTORS.OPERATOR.defaultInfluence, 1);
    expect(op.continuity.healthy).toBe(true);
  });

  test("being constitution passes for seeded beings", () => {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  test("being mutations emit events and preserve identity", () => {
    resetDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    getDaedalusEventBus().subscribe(e => events.push(e));

    daedalusStore.updateBeingPresence("operator", { posture: "sentinel" });

    const ev = events.find(e => e.type === "BEING_PRESENCE_UPDATED");
    expect(ev).toBeDefined();
    expect(ev!.beingPresence!.id).toBe("operator");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 3. ATTENTION LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("3. Attention", () => {
  test("dominant being's attention becomes system attention", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) beings[b.id] = b;
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const dominant = beings[behavioral.dominantBeingId!];
    expect(field.attention.level).toBe(dominant.attention.level);
  });

  test("idle expressive attention defaults to aware", () => {
    expect(IDLE_EXPRESSIVE.attention.level).toBe("aware");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 4. CONTINUITY LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("4. Continuity", () => {
  test("anchor being is identified from seeded beings", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) beings[b.id] = b;
    const signals = narrateContinuity(beings);

    if (Object.keys(beings).length > 1) {
      const maxStreak = Math.max(...Object.values(beings).map(b => b.continuity.streak));
      if (maxStreak > 3) {
        const anchor = signals.find(s => s.kind === "anchor");
        expect(anchor).toBeDefined();
      }
    }
  });

  test("identity continuity rises with streak depth", () => {
    expect(computeIdentityContinuity(1, 1, 5)).toBeLessThan(computeIdentityContinuity(1, 1, 25));
  });

  test("drift-recovery fires on unhealthy → healthy transition", () => {
    const op = daedalusStore.getBeingPresence("operator")!;
    const beings: Record<string, BeingPresenceDetail> = {
      [op.id]: { ...op, continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } },
    };
    const signals = narrateContinuity(beings, { [op.id]: false });
    expect(signals.find(s => s.kind === "drift-recovery")).toBeDefined();
  });

  test("continuity health labels are correct", () => {
    expect(deriveContinuityHealth(0.8)).toBe("healthy");
    expect(deriveContinuityHealth(0.5)).toBe("shifting");
    expect(deriveContinuityHealth(0.2)).toBe("fragile");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 5. CAPABILITIES LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("5. Capabilities", () => {
  test("negotiation preview returns decision without side effects", async () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("cap-preview-node"));

    const res = await request(app)
      .post("/daedalus/negotiations/preview")
      .send({ requestedBy: { id: "operator" }, targetNodeId: "cap-preview-node", capabilityName: "core", desiredEnabled: false });
    expect(res.status).toBe(200);
    expect(res.body.decisions).toHaveLength(1);
    expect(res.body.decisions[0].fromEnabled).toBe(true);
    expect(res.body.decisions[0].toEnabled).toBe(false);
  });

  test("capability trace includes all levels", async () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("cap-trace-node"));

    const res = await request(app)
      .get("/daedalus/capabilities/trace?nodeId=cap-trace-node&capabilityName=core");
    expect(res.status).toBe(200);
    expect(res.body.steps.length).toBeGreaterThanOrEqual(2);
    const levels = res.body.steps.map((s: any) => s.level);
    expect(levels).toContain("node");
    expect(levels).toContain("governance");
  });

  test("mirror cap sync validates and rejects duplicates", () => {
    const reg = new NodeMirrorRegistry();
    reg.handleJoin(mkJoin("cap-test"));
    const deltas = reg.handleCapSync({
      nodeId: "cap-test",
      capabilities: [
        { name: "core", value: "enabled", enabled: true },
        { name: "core", value: "disabled", enabled: false },
      ],
      timestamp: new Date().toISOString(),
    });
    expect(deltas).toEqual([]);
    expect(reg.getMirror("cap-test")!.lifecycle.errorCount).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 6. EXPRESSIVE PHYSIOLOGY LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("6. Expressive physiology", () => {
  test("glow derives from phase correctly", () => {
    const active = deriveGlowFromPhase("active", { level: "medium", intensity: 0.5 });
    expect(active.level).toBe("high");
    expect(active.intensity).toBeGreaterThanOrEqual(0.7);

    const quarantined = deriveGlowFromPhase("quarantined", { level: "high", intensity: 1 });
    expect(quarantined.level).toBe("none");
    expect(quarantined.intensity).toBe(0);
  });

  test("posture derives from phase correctly", () => {
    expect(derivePostureFromPhase("active")).toBe("companion");
    expect(derivePostureFromPhase("degraded")).toBe("observer");
    expect(derivePostureFromPhase("quarantined")).toBe("dormant");
  });

  test("expressive field stability reflects being health", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) beings[b.id] = b;
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);
    const expected = Object.values(beings).filter(b => b.continuity.healthy).length / Object.values(beings).length;
    expect(field.stability).toBeCloseTo(expected, 1);
  });

  test("fallback defaults when no beings", () => {
    const behavioral = computeBehavioralField({});
    const field = computeExpressiveField({}, behavioral);
    expect(field.posture).toBe(EXPRESSIVE_DEFAULTS.fallbackPosture);
    expect(field.stability).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 7. GOVERNANCE LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("7. Governance", () => {
  let gov: GovernanceService;
  beforeEach(() => { resetDaedalusEventBus(); gov = new GovernanceService(); });

  test("posture precedence: LOCKDOWN > GUARDED > ATTENTIVE > OPEN", () => {
    expect(gov.getPostureSnapshot().posture).toBe("OPEN");

    gov.castVote({ being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 1 });
    expect(gov.getPostureSnapshot().posture).toBe("ATTENTIVE");

    gov.recordDrift({ severity: "HIGH", summary: "critical" });
    expect(gov.getPostureSnapshot().posture).toBe("GUARDED");

    gov.applyOverride({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "Emergency", scope: "GLOBAL", effect: "DENY" });
    expect(gov.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("override removal restores posture", () => {
    const override = gov.applyOverride({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "Test", scope: "GLOBAL", effect: "DENY" });
    expect(gov.getPostureSnapshot().posture).toBe("LOCKDOWN");

    gov.removeOverride(override.id);
    expect(gov.getPostureSnapshot().posture).toBe("OPEN");
  });

  test("posture snapshot always reflects current overrides/drifts", () => {
    gov.applyOverride({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "1", scope: "NODE", targetId: "n1", effect: "ALLOW" });
    gov.applyOverride({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "2", scope: "NODE", targetId: "n2", effect: "ALLOW" });
    expect(gov.getPostureSnapshot().activeOverrides).toHaveLength(2);
  });

  test("vote-weighted posture: majority DENY → LOCKDOWN", () => {
    gov.castVote({ being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "DENY", weight: 0.8 });
    gov.castVote({ being: { id: "g1", role: "GUARDIAN", label: "G1" }, vote: "ALLOW", weight: 0.2 });
    expect(gov.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 8. EVENT STREAM LAYER
// ═══════════════════════════════════════════════════════════════════════

describe("8. Events", () => {
  test("event bus delivers to all subscribers synchronously", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const a: DaedalusEventPayload[] = [];
    const b: DaedalusEventPayload[] = [];
    bus.subscribe(e => a.push(e));
    bus.subscribe(e => b.push(e));

    bus.publish({ type: "POSTURE_CHANGED", timestamp: new Date().toISOString(), posture: "OPEN", summary: "test" });
    expect(a).toHaveLength(1);
    expect(b).toHaveLength(1);
  });

  test("mirror events bridge to event bus", () => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    const bus = getDaedalusEventBus();
    const events: DaedalusEventPayload[] = [];
    bus.subscribe(e => events.push(e));

    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("bridge-test"));

    const joinEvent = events.find(e => e.type === "MIRROR_NODE_JOINED");
    expect(joinEvent).toBeDefined();
    expect(joinEvent!.nodeId).toBe("bridge-test");
  });

  test("SSE endpoint streams events", (done) => {
    const req = supertest(app)
      .get("/daedalus/events")
      .set("x-daedalus-token", TOKEN)
      .buffer(false)
      .parse((res: any, callback: any) => {
        let data = "";
        res.on("data", (chunk: Buffer) => {
          data += chunk.toString();
          if (data.includes("daedalus-events-stream-open")) {
            expect(res.headers["content-type"]).toContain("text/event-stream");
            res.destroy();
            callback(null, data);
          }
        });
        res.on("end", () => callback(null, data));
      })
      .end(() => done());
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 9. PERSISTENCE (COLD START)
// ═══════════════════════════════════════════════════════════════════════

describe("9. Persistence & cold start", () => {
  test("cold start seeds operator and guardian beings", () => {
    const beings = daedalusStore.getBeingPresences();
    const ids = beings.map(b => b.id);
    expect(ids).toContain("operator");
    expect(ids).toContain("guardian-1");
  });

  test("cold start mirror registry starts empty (nodes join at runtime)", () => {
    const reg = new NodeMirrorRegistry();
    expect(reg.getCount()).toBe(0);
  });

  test("mirror registry starts empty (nodes must re-join)", () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    expect(reg.getCount()).toBe(0);
  });

  test("governance starts OPEN with no overrides/drifts/votes", () => {
    const gov = new GovernanceService();
    expect(gov.getPostureSnapshot().posture).toBe("OPEN");
    expect(gov.listOverrides()).toHaveLength(0);
    expect(gov.listDrifts()).toHaveLength(0);
    expect(gov.listVotes()).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 10. OPERATOR EXPERIENCE
// ═══════════════════════════════════════════════════════════════════════

describe("10. Operator experience", () => {
  test("operator can view all beings", async () => {
    const res = await request(app).get("/daedalus/beings/presence").expect(200);
    expect(res.body.length).toBeGreaterThanOrEqual(2);
  });

  test("operator can update being presence", async () => {
    const res = await request(app).put("/daedalus/beings/operator/presence")
      .send({ posture: "observer" }).expect(200);
    expect(res.body.posture).toBe("observer");
  });

  test("operator can create and remove governance overrides", async () => {
    const create = await request(app).post("/daedalus/governance/overrides")
      .send({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "Test", scope: "NODE", targetId: "n1", effect: "ALLOW" })
      .expect(201);
    const id = create.body.id;
    expect(id).toBeDefined();

    await request(app).delete(`/daedalus/governance/overrides/${id}`).expect(204);
  });

  test("operator can cast and clear votes", async () => {
    await request(app).post("/daedalus/governance/votes")
      .send({ being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 0.5 })
      .expect(201);

    await request(app).delete("/daedalus/governance/votes").expect(204);

    const res = await request(app).get("/daedalus/governance/votes").expect(200);
    expect(res.body).toHaveLength(0);
  });

  test("operator can view cockpit node cortex", async () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("cortex-test"));

    const res = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    expect(res.body.length).toBeGreaterThanOrEqual(1);
    expect(res.body[0]).toHaveProperty("glow");
    expect(res.body[0]).toHaveProperty("posture");
    expect(res.body[0]).toHaveProperty("risk");
    expect(res.body[0]).toHaveProperty("errorCount");
  });

  test("operator can view governance posture", async () => {
    const res = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(res.body.posture);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 11. NODE FABRIC
// ═══════════════════════════════════════════════════════════════════════

describe("11. Node fabric", () => {
  test("node join → heartbeat → quarantine → detach lifecycle", () => {
    const mirror = processJoin(createFreshMirror("lifecycle"), mkJoin("lifecycle"));
    expect(mirror.lifecycle.phase).toBe("active");

    const hb = processHeartbeat(mirror, { nodeId: "lifecycle", timestamp: new Date().toISOString(), status: "alive" });
    expect(hb.lifecycle.heartbeatCount).toBe(1);

    const degraded = processHeartbeat(hb, { nodeId: "lifecycle", timestamp: new Date().toISOString(), status: "degraded" });
    expect(degraded.lifecycle.phase).toBe("degraded");

    const recovered = processHeartbeat(degraded, { nodeId: "lifecycle", timestamp: new Date().toISOString(), status: "alive" });
    expect(recovered.lifecycle.phase).toBe("active");

    const q = processQuarantine(recovered);
    expect(q.lifecycle.phase).toBe("quarantined");
    expect(q.risk).toBe("high");

    const d = processDetach(q);
    expect(d.lifecycle.phase).toBe("detached");
  });

  test("phase transition table is locked", () => {
    expect(canTransitionPhase("detached", "active")).toBe(false);
    expect(canTransitionPhase("quarantined", "active")).toBe(false);
    expect(canTransitionPhase("active", "quarantined")).toBe(true);
    expect(canTransitionPhase("degraded", "active")).toBe(true);
  });

  test("error threshold auto-quarantine works", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoin("err-test"));
    reg.handleError("err-test", "e1");
    reg.handleError("err-test", "e2");
    reg.handleError("err-test", "e3");
    expect(reg.getMirror("err-test")!.lifecycle.phase).toBe("quarantined");
  });

  test("stale heartbeat detection works", () => {
    const reg = new NodeMirrorRegistry();
    reg.configureSafety({ staleHeartbeatMs: 1000, errorQuarantineThreshold: 100 });
    reg.handleJoin(mkJoin("stale-test"));
    reg.handleHeartbeat({ nodeId: "stale-test", timestamp: new Date().toISOString(), status: "alive" });
    const stale = reg.sweepStaleHeartbeats(Date.now() + 5000);
    expect(stale).toContain("stale-test");
  });

  test("mirror HTTP routes are functional", async () => {
    resetNodeMirrorRegistry();
    const join = await request(app).post("/daedalus/mirror/join").send(mkJoin("http-fabric")).expect(201);
    expect(join.body.nodeId).toBe("http-fabric");

    const hb = await request(app).post("/daedalus/mirror/heartbeat")
      .send({ nodeId: "http-fabric", timestamp: new Date().toISOString(), status: "alive" }).expect(200);
    expect(hb.body.phase).toBe("active");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 12. ORCHESTRATOR (CENTRAL NERVOUS SYSTEM)
// ═══════════════════════════════════════════════════════════════════════

describe("12. Orchestrator", () => {
  test("snapshot returns coherent view of nodes and beings", async () => {
    const res = await request(app).get("/daedalus/snapshot").expect(200);
    expect(res.body.nodes).toBeDefined();
    expect(res.body.beings).toBeDefined();
    expect(res.body.nodes.length).toBeGreaterThanOrEqual(1);
    expect(res.body.beings.length).toBeGreaterThanOrEqual(1);
  });

  test("cockpit summary aggregates correctly", async () => {
    const res = await request(app).get("/daedalus/cockpit/summary").expect(200);
    expect(res.body).toHaveProperty("totalNodes");
    expect(res.body).toHaveProperty("byStatus");
    expect(res.body).toHaveProperty("byPosture");
    expect(res.body).toHaveProperty("byRisk");
    expect(res.body).toHaveProperty("totalErrors");
  });

  test("safety envelope has correct defaults", () => {
    const reg = new NodeMirrorRegistry();
    const safety = reg.getSafety();
    expect(safety.errorQuarantineThreshold).toBe(5);
    expect(safety.staleHeartbeatMs).toBe(30_000);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 13. COCKPIT (SENSORY CORTEX)
// ═══════════════════════════════════════════════════════════════════════

describe("13. Cockpit", () => {
  test("node list returns complete card data", async () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    reg.handleJoin(mkJoin("cockpit-card"));
    reg.handleHeartbeat({ nodeId: "cockpit-card", timestamp: new Date().toISOString(), status: "alive" });

    const res = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    const node = res.body.find((n: any) => n.id === "cockpit-card");
    expect(node).toBeDefined();
    expect(node).toHaveProperty("name");
    expect(node).toHaveProperty("status");
    expect(node).toHaveProperty("risk");
    expect(node).toHaveProperty("phase");
    expect(node).toHaveProperty("glow");
    expect(node).toHaveProperty("glowIntensity");
    expect(node).toHaveProperty("posture");
    expect(node).toHaveProperty("attention");
    expect(node).toHaveProperty("continuity");
    expect(node).toHaveProperty("capabilities");
    expect(node).toHaveProperty("heartbeatCount");
    expect(node).toHaveProperty("lastHeartbeatAt");
    expect(node).toHaveProperty("errorCount");
  });

  test("being presence is visible from cockpit", async () => {
    const res = await request(app).get("/daedalus/beings/presence").expect(200);
    for (const being of res.body) {
      expect(being).toHaveProperty("posture");
      expect(being).toHaveProperty("glow");
      expect(being).toHaveProperty("attention");
      expect(being).toHaveProperty("continuity");
      expect(being).toHaveProperty("influenceLevel");
    }
  });

  test("governance posture is visible from cockpit", async () => {
    const res = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(res.body).toHaveProperty("posture");
    expect(res.body).toHaveProperty("reason");
    expect(res.body).toHaveProperty("since");
    expect(res.body).toHaveProperty("activeOverrides");
    expect(res.body).toHaveProperty("activeDrifts");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 14. WHOLE-BEING COHERENCE — The Final Test
// ═══════════════════════════════════════════════════════════════════════

describe("14. Whole-being coherence", () => {
  test("end-to-end: node join → mirror → event → cockpit view", async () => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    const events: DaedalusEventPayload[] = [];
    getDaedalusEventBus().subscribe(e => events.push(e));

    await request(app).post("/daedalus/mirror/join").send(mkJoin("e2e-node")).expect(201);

    const joinEvent = events.find(e => e.type === "MIRROR_NODE_JOINED" && e.nodeId === "e2e-node");
    expect(joinEvent).toBeDefined();

    const cockpit = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    const node = cockpit.body.find((n: any) => n.id === "e2e-node");
    expect(node).toBeDefined();
    expect(node.phase).toBe("active");
    expect(node.posture).toBe("companion");
    expect(node.glow).toBe("high");
  });

  test("end-to-end: being update → expressive field → system posture", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) beings[b.id] = b;
    beings["operator"] = { ...beings["operator"], posture: "sentinel", glow: { level: "low", intensity: 0.2 } };

    const behavioral = computeBehavioralField(beings);
    expect(behavioral.dominantBeingId).toBe("operator");

    const field = computeExpressiveField(beings, behavioral);
    expect(field.posture).toBe("sentinel");
    expect(field.glow.level).toBe("low");
  });

  test("end-to-end: governance override → posture change → cockpit visible", async () => {
    const create = await request(app).post("/daedalus/governance/overrides")
      .send({ createdBy: { id: "op", role: "OPERATOR", label: "Op" }, reason: "Lock it down", scope: "GLOBAL", effect: "DENY" })
      .expect(201);

    const posture = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(posture.body.posture).toBe("LOCKDOWN");

    await request(app).delete(`/daedalus/governance/overrides/${create.body.id}`).expect(204);
    const after = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(after.body.posture).not.toBe("LOCKDOWN");
  });

  test("end-to-end: error accumulation → auto-quarantine → cockpit reflects", async () => {
    resetNodeMirrorRegistry();
    const reg = getNodeMirrorRegistry();
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoin("fragile-node"));

    reg.handleError("fragile-node", "err1");
    reg.handleError("fragile-node", "err2");
    reg.handleError("fragile-node", "err3");

    const cockpit = await request(app).get("/daedalus/cockpit/nodes").expect(200);
    const node = cockpit.body.find((n: any) => n.id === "fragile-node");
    expect(node.phase).toBe("quarantined");
    expect(node.risk).toBe("high");
    expect(node.errorCount).toBe(3);
  });

  test("end-to-end: being continuity → identity continuity → system health", () => {
    const beings: Record<string, BeingPresenceDetail> = {};
    for (const b of daedalusStore.getBeingPresences()) beings[b.id] = b;

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    const signals = narrateContinuity(beings);
    const anchorSignal = signals.find(s => s.kind === "anchor");
    const bestStreak = Math.max(...Object.values(beings).map(b => b.continuity.streak));

    const sys = computeSystemContinuity({
      beingStability: field.stability,
      beingCount: Object.keys(beings).length,
      bestStreak,
      driftSignalCount: signals.filter(s => s.kind === "drift-recovery").length,
      anchorBeingId: anchorSignal?.beingId ?? CANONICAL_ANCHOR_BEING_ID,
      orchestrationStability: 0.8,
      continuityBlend: 0.9,
      embodiedContinuity: 0.8,
      motionGrammar: 0.8,
      timelineMomentum: 0.7,
      persistenceRestored: true,
    });

    expect(sys.health).toBe("healthy");
    expect(sys.anchorBeingId).toBeDefined();
    expect(sys.composite).toBeGreaterThan(0.7);
  });

  test("Daedalus is one being: identity + continuity + governance + beings + fabric + cockpit are coherent", () => {
    expect(DAEDALUS_IDENTITY.name).toBe("Daedalus");
    expect(DAEDALUS_IDENTITY.operatorId).toBe(CANONICAL_OPERATOR_ID);
    expect(daedalusStore.getBeingPresence("operator")).toBeDefined();

    const beings = daedalusStore.getBeingPresences();
    const report = validateBeingConstitution(beings);
    expect(report.allPassed).toBe(true);

    const gov = new GovernanceService();
    expect(gov.getPostureSnapshot().posture).toBe("OPEN");

    const reg = new NodeMirrorRegistry();
    expect(reg.getSafety().errorQuarantineThreshold).toBe(5);

    expect(GLOW_PALETTE.high.hex).toMatch(/^#/);
    expect(BEING_POSTURE_ARCHETYPES).toContain("sentinel");

    expect(IDLE_EXPRESSIVE.continuity.healthy).toBe(true);
  });
});
