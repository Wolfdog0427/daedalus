import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { DaedalusEventBus, getDaedalusEventBus, resetDaedalusEventBus, DaedalusEventPayload } from "../orchestrator/DaedalusEventBus";

describe("GovernanceService unit tests", () => {
  it("starts with OPEN posture", () => {
    const svc = new GovernanceService();
    expect(svc.getPostureSnapshot().posture).toBe("OPEN");
  });

  it("applies an override and lists it", () => {
    const svc = new GovernanceService();
    const o = svc.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
      reason: "test override",
      scope: "NODE",
      targetId: "n1",
      effect: "DENY",
    });
    expect(o.id).toBeDefined();
    expect(o.createdAt).toBeDefined();
    expect(svc.listOverrides()).toHaveLength(1);
  });

  it("records a drift and lists it", () => {
    const svc = new GovernanceService();
    const d = svc.recordDrift({ severity: "MEDIUM", summary: "test drift" });
    expect(d.id).toBeDefined();
    expect(d.detectedAt).toBeDefined();
    expect(svc.listDrifts()).toHaveLength(1);
  });

  it("escalates posture to ATTENTIVE on medium drift", () => {
    const svc = new GovernanceService();
    svc.recordDrift({ severity: "MEDIUM", summary: "medium drift" });
    expect(svc.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  it("escalates posture to GUARDED on high drift", () => {
    const svc = new GovernanceService();
    svc.recordDrift({ severity: "HIGH", summary: "severe drift" });
    expect(svc.getPostureSnapshot().posture).toBe("GUARDED");
  });

  it("escalates posture to LOCKDOWN on global deny", () => {
    const svc = new GovernanceService();
    svc.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
      reason: "lockdown",
      scope: "GLOBAL",
      effect: "DENY",
    });
    expect(svc.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  it("publishes POSTURE_CHANGED when posture transitions", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    const svc = new GovernanceService();
    svc.recordDrift({ severity: "HIGH", summary: "severe" });

    const postureEvents = received.filter((e) => e.type === "POSTURE_CHANGED");
    expect(postureEvents.length).toBeGreaterThanOrEqual(1);
    expect(postureEvents[0].posture).toBe("GUARDED");
  });

  it("publishes GOVERNANCE_OVERRIDE_APPLIED on override", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    const svc = new GovernanceService();
    svc.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Op" },
      reason: "test",
      scope: "NODE",
      effect: "ALLOW",
    });

    expect(received.some((e) => e.type === "GOVERNANCE_OVERRIDE_APPLIED")).toBe(true);
  });

  it("publishes CONTINUITY_DRIFT_DETECTED on drift", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    const svc = new GovernanceService();
    svc.recordDrift({ severity: "LOW", summary: "minor" });

    expect(received.some((e) => e.type === "CONTINUITY_DRIFT_DETECTED")).toBe(true);
  });
});

describe("Governance HTTP endpoints", () => {
  const app = createOrchestratorApp();

  it("GET /daedalus/governance/posture returns posture snapshot", async () => {
    const res = await request(app).get("/daedalus/governance/posture").expect(200);
    expect(res.body.posture).toBeDefined();
    expect(res.body.reason).toBeDefined();
  });

  it("GET /daedalus/governance/overrides returns array", async () => {
    const res = await request(app).get("/daedalus/governance/overrides").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it("POST /daedalus/governance/overrides creates an override", async () => {
    const res = await request(app)
      .post("/daedalus/governance/overrides")
      .send({
        createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
        reason: "HTTP test override",
        scope: "CAPABILITY",
        targetId: "negotiation",
        effect: "ESCALATE",
      })
      .expect(201);

    expect(res.body.id).toBeDefined();
    expect(res.body.reason).toBe("HTTP test override");
  });

  it("GET /daedalus/governance/drifts returns array", async () => {
    const res = await request(app).get("/daedalus/governance/drifts").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it("POST /daedalus/governance/drifts records a drift", async () => {
    const res = await request(app)
      .post("/daedalus/governance/drifts")
      .send({ severity: "LOW", summary: "HTTP test drift" })
      .expect(201);

    expect(res.body.id).toBeDefined();
    expect(res.body.summary).toBe("HTTP test drift");
  });
});
