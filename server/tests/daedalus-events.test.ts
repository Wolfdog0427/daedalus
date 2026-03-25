import { DaedalusEventBus, DaedalusEventPayload } from "../orchestrator/DaedalusEventBus";
import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";

describe("DaedalusEventBus", () => {
  it("notifies subscribers on publish", () => {
    const bus = new DaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    const unsubscribe = bus.subscribe((event) => received.push(event));

    const event: DaedalusEventPayload = {
      type: "STRATEGY_CHANGED",
      timestamp: "2024-01-01T00:00:00Z",
      summary: "Strategy changed",
      strategy: "default",
      alignment: 92,
    };
    bus.publish(event);

    expect(received).toHaveLength(1);
    expect(received[0]).toEqual(event);

    unsubscribe();
  });

  it("stops notifying after unsubscribe", () => {
    const bus = new DaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    const unsubscribe = bus.subscribe((event) => received.push(event));

    bus.publish({
      type: "STRATEGY_CHANGED",
      timestamp: "2024-01-01T00:00:00Z",
      summary: "Strategy changed",
    });
    expect(received).toHaveLength(1);

    unsubscribe();

    bus.publish({
      type: "ALIGNMENT_ESCALATION",
      timestamp: "2024-01-01T00:00:01Z",
      summary: "Escalation",
    });
    expect(received).toHaveLength(1);
  });

  it("does not throw when a listener fails", () => {
    const bus = new DaedalusEventBus();
    bus.subscribe(() => {
      throw new Error("boom");
    });

    expect(() =>
      bus.publish({
        type: "SAFE_MODE_ACTIVE",
        timestamp: "2024-01-01T00:00:00Z",
        summary: "Safe mode active",
      }),
    ).not.toThrow();
  });

  it("supports multiple subscribers", () => {
    const bus = new DaedalusEventBus();
    const a: DaedalusEventPayload[] = [];
    const b: DaedalusEventPayload[] = [];
    bus.subscribe((e) => a.push(e));
    bus.subscribe((e) => b.push(e));

    bus.publish({
      type: "NEGOTIATION_COMPLETED",
      timestamp: "2024-01-01T00:00:00Z",
      nodeId: "n1",
      summary: "done",
    });

    expect(a).toHaveLength(1);
    expect(b).toHaveLength(1);
  });
});

describe("GET /daedalus/events SSE endpoint", () => {
  const app = createOrchestratorApp();

  it("responds with text/event-stream content type", (done) => {
    const req = request(app)
      .get("/daedalus/events")
      .buffer(false)
      .parse((res: any, callback: any) => {
        let data = "";
        res.on("data", (chunk: Buffer) => {
          data += chunk.toString();
          if (data.includes("daedalus-events-stream-open")) {
            (res as any).destroy();
          }
        });
        res.on("end", () => callback(null, data));
        res.on("close", () => callback(null, data));
      })
      .end((err: any, res: any) => {
        expect(res.headers["content-type"]).toContain("text/event-stream");
        done();
      });
  });
});

describe("Negotiation emits SSE events", () => {
  it("publishes events when a negotiation changes state", async () => {
    const { DaedalusEventBus, getDaedalusEventBus, resetDaedalusEventBus } =
      require("../orchestrator/DaedalusEventBus");

    resetDaedalusEventBus();
    const bus = getDaedalusEventBus();

    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e: DaedalusEventPayload) => received.push(e));

    const app = createOrchestratorApp();

    const snapshotRes = await request(app).get("/daedalus/snapshot").expect(200);
    const node = snapshotRes.body.nodes.find(
      (n: any) => n.capabilities.some((c: any) => c.enabled),
    );

    if (!node) return;

    const cap = node.capabilities.find((c: any) => c.enabled);

    await request(app)
      .post("/daedalus/negotiations/apply")
      .send({
        requestedBy: { id: "operator" },
        targetNodeId: node.id,
        capabilityName: cap.name,
        desiredEnabled: false,
      })
      .expect(200);

    const negotiationEvents = received.filter(
      (e) => e.type === "NEGOTIATION_COMPLETED",
    );
    expect(negotiationEvents.length).toBeGreaterThanOrEqual(1);
    expect(negotiationEvents[0].nodeId).toBe(node.id);
  });
});
