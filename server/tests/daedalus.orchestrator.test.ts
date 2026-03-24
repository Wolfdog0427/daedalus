import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  CapabilityTrace,
  NegotiationApplyResult,
  NegotiationPreview,
  OrchestratorSnapshot,
} from "../../shared/daedalus/contracts";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";

function seedTestNode() {
  resetNodeMirrorRegistry();
  const reg = getNodeMirrorRegistry();
  reg.handleJoin({
    nodeId: "test-node",
    name: "Test Node",
    capabilities: [
      { name: "negotiation", value: "enabled", enabled: true },
      { name: "capability-trace", value: "enabled", enabled: true },
    ],
    expressive: { glow: { level: "medium", intensity: 0.5 }, posture: "companion" as const, attention: { level: "aware" }, continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true } },
    profile: { id: "test-node", name: "Test Node", kind: "server" as const, model: "test", os: "test", osVersion: "1.0", operatorId: "operator" },
  });
}

describe("Daedalus Orchestrator", () => {
  const app = createOrchestratorApp();

  beforeEach(() => seedTestNode());
  afterAll(() => resetNodeMirrorRegistry());

  it("returns a snapshot with nodes and beings", async () => {
    const res = await request(app).get("/daedalus/snapshot").expect(200);
    const body = res.body as OrchestratorSnapshot;

    expect(Array.isArray(body.nodes)).toBe(true);
    expect(Array.isArray(body.beings)).toBe(true);
    expect(body.nodes.length).toBeGreaterThan(0);
    expect(body.beings.length).toBeGreaterThan(0);
  });

  it("returns nodes list", async () => {
    const res = await request(app).get("/daedalus/nodes").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThan(0);
  });

  it("returns a capability trace for an existing capability", async () => {
    const res = await request(app)
      .get("/daedalus/capabilities/trace")
      .query({ nodeId: "test-node", capabilityName: "negotiation" })
      .expect(200);

    const trace = res.body as CapabilityTrace;
    expect(trace.nodeId).toBe("test-node");
    expect(trace.capabilityName).toBe("negotiation");
    expect(Array.isArray(trace.steps)).toBe(true);
  });

  it("returns 404 for trace on unknown node", async () => {
    const res = await request(app)
      .get("/daedalus/capabilities/trace")
      .query({ nodeId: "unknown-node", capabilityName: "whatever" })
      .expect(404);

    expect(res.body.error).toBeDefined();
  });

  it("previews a negotiation", async () => {
    const payload = {
      requestedBy: { id: "operator" },
      targetNodeId: "test-node",
      capabilityName: "negotiation",
      desiredEnabled: false,
    };

    const res = await request(app)
      .post("/daedalus/negotiations/preview")
      .send(payload)
      .expect(200);

    const preview = res.body as NegotiationPreview;
    expect(preview.nodeId).toBe("test-node");
    expect(preview.decisions.length).toBe(1);
    expect(preview.decisions[0].capabilityName).toBe("negotiation");
  });

  it("applies a negotiation", async () => {
    const payload = {
      requestedBy: { id: "operator" },
      targetNodeId: "test-node",
      capabilityName: "negotiation",
      desiredEnabled: false,
    };

    const res = await request(app)
      .post("/daedalus/negotiations/apply")
      .send(payload)
      .expect(200);

    const result = res.body as NegotiationApplyResult;
    expect(result.nodeId).toBe("test-node");
    expect(result.decisions.length).toBe(1);
  });
});
