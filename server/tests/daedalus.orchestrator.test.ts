import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  CapabilityTrace,
  NegotiationApplyResult,
  NegotiationPreview,
  OrchestratorSnapshot,
} from "../../shared/daedalus/contracts";

describe("Daedalus Orchestrator", () => {
  const app = createOrchestratorApp();

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
    const snapshotRes = await request(app).get("/daedalus/snapshot").expect(200);
    const snapshot = snapshotRes.body as OrchestratorSnapshot;
    const node = snapshot.nodes[0];
    const cap = node.capabilities[0];

    const res = await request(app)
      .get("/daedalus/capabilities/trace")
      .query({ nodeId: node.id, capabilityName: cap.name })
      .expect(200);

    const trace = res.body as CapabilityTrace;
    expect(trace.nodeId).toBe(node.id);
    expect(trace.capabilityName).toBe(cap.name);
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
    const snapshotRes = await request(app).get("/daedalus/snapshot").expect(200);
    const snapshot = snapshotRes.body as OrchestratorSnapshot;
    const node = snapshot.nodes[0];
    const cap = node.capabilities[0];

    const payload = {
      requestedBy: { id: "operator" },
      targetNodeId: node.id,
      capabilityName: cap.name,
      desiredEnabled: !cap.enabled,
    };

    const res = await request(app)
      .post("/daedalus/negotiations/preview")
      .send(payload)
      .expect(200);

    const preview = res.body as NegotiationPreview;
    expect(preview.nodeId).toBe(node.id);
    expect(preview.decisions.length).toBe(1);
    expect(preview.decisions[0].capabilityName).toBe(cap.name);
  });

  it("applies a negotiation", async () => {
    const snapshotRes = await request(app).get("/daedalus/snapshot").expect(200);
    const snapshot = snapshotRes.body as OrchestratorSnapshot;
    const node = snapshot.nodes[0];
    const cap = node.capabilities[0];

    const payload = {
      requestedBy: { id: "operator" },
      targetNodeId: node.id,
      capabilityName: cap.name,
      desiredEnabled: !cap.enabled,
    };

    const res = await request(app)
      .post("/daedalus/negotiations/apply")
      .send(payload)
      .expect(200);

    const result = res.body as NegotiationApplyResult;
    expect(result.nodeId).toBe(node.id);
    expect(result.decisions.length).toBe(1);
  });
});
