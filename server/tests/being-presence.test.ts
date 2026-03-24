import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { daedalusStore } from "../orchestrator/daedalusStore";

describe("Being Presence HTTP endpoints", () => {
  const app = createOrchestratorApp();

  it("GET /daedalus/beings/presence returns seeded beings", async () => {
    const res = await request(app).get("/daedalus/beings/presence").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThanOrEqual(2);
    expect(res.body[0].id).toBeDefined();
    expect(res.body[0].posture).toBeDefined();
    expect(res.body[0].influenceLevel).toBeDefined();
  });

  it("GET /daedalus/beings/:id/presence returns a single being", async () => {
    const res = await request(app)
      .get("/daedalus/beings/operator/presence")
      .expect(200);
    expect(res.body.id).toBe("operator");
    expect(res.body.name).toBe("Operator");
    expect(res.body.glow).toBeDefined();
    expect(res.body.glow.level).toBe("high");
  });

  it("GET /daedalus/beings/:id/presence returns 404 for unknown being", async () => {
    await request(app)
      .get("/daedalus/beings/nonexistent/presence")
      .expect(404);
  });

  it("PUT /daedalus/beings/:id/presence patches and returns updated being", async () => {
    const res = await request(app)
      .put("/daedalus/beings/operator/presence")
      .send({ presenceMode: "dominant", isSpeaking: true })
      .expect(200);

    expect(res.body.presenceMode).toBe("dominant");
    expect(res.body.isSpeaking).toBe(true);
    expect(res.body.id).toBe("operator");
    expect(res.body.updatedAt).toBeDefined();
  });

  it("PUT /daedalus/beings/:id/presence returns 404 for unknown being", async () => {
    await request(app)
      .put("/daedalus/beings/nonexistent/presence")
      .send({ presenceMode: "idle" })
      .expect(404);
  });
});

describe("Being Presence SSE events", () => {
  it("publishes BEING_PRESENCE_UPDATED on update", () => {
    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    daedalusStore.updateBeingPresence("guardian-1", {
      presenceMode: "active",
      influenceLevel: 0.8,
    });

    const presenceEvents = received.filter(
      (e) => e.type === "BEING_PRESENCE_UPDATED",
    );
    expect(presenceEvents.length).toBe(1);
    expect(presenceEvents[0].beingId).toBe("guardian-1");
    expect(presenceEvents[0].beingPresence?.presenceMode).toBe("active");
    expect(presenceEvents[0].beingPresence?.influenceLevel).toBe(0.8);
  });
});

describe("DaedalusStore being presence", () => {
  it("getBeingPresences returns all beings", () => {
    const beings = daedalusStore.getBeingPresences();
    expect(beings.length).toBeGreaterThanOrEqual(2);
  });

  it("getBeingPresence returns a specific being", () => {
    const being = daedalusStore.getBeingPresence("operator");
    expect(being).toBeDefined();
    expect(being?.name).toBe("Operator");
  });

  it("getBeingPresence returns undefined for unknown being", () => {
    expect(daedalusStore.getBeingPresence("ghost")).toBeUndefined();
  });

  it("updateBeingPresence returns null for unknown being", () => {
    expect(
      daedalusStore.updateBeingPresence("ghost", { presenceMode: "idle" }),
    ).toBeNull();
  });

  it("updateBeingPresence preserves unpatched fields", () => {
    const before = daedalusStore.getBeingPresence("operator");
    daedalusStore.updateBeingPresence("operator", { isGuiding: false });
    const after = daedalusStore.getBeingPresence("operator");

    expect(after?.isGuiding).toBe(false);
    expect(after?.name).toBe(before?.name);
    expect(after?.posture).toBe(before?.posture);
  });
});
