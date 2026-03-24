/**
 * RED-TEAM SECURITY PASS
 *
 * Simulates an external attacker who didn't build the system trying to:
 *   1. Bypass authentication
 *   2. Exfiltrate sensitive data
 *   3. Poison/corrupt state
 *   4. Denial-of-service via spam
 *   5. Injection attacks (XSS, path traversal, prototype pollution)
 *   6. Header manipulation
 *   7. SSRF / internal endpoint probing
 *   8. Token brute-force / timing attacks
 *   9. State corruption via malformed payloads
 *  10. Resource exhaustion
 *
 * This test runs with NODE_ENV !== "test" to exercise the REAL auth middleware.
 */

import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import {
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";
import { resetRateLimits } from "../orchestrator/middleware/rateLimit";

const VALID_TOKEN = process.env.DAEDALUS_TOKEN ?? "daedalus-dev-token";

describe("RED-TEAM SECURITY PASS", () => {
  const app = createOrchestratorApp();

  beforeAll(() => {
    process.env.NODE_ENV = "production";
  });

  beforeEach(() => {
    resetRateLimits();
  });

  afterAll(() => {
    process.env.NODE_ENV = "test";
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    resetRateLimits();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 1. AUTHENTICATION BYPASS ATTEMPTS
  // ═══════════════════════════════════════════════════════════════════════
  describe("Auth bypass", () => {
    test("no token → 401 on all protected routes", async () => {
      const routes = [
        { method: "get", path: "/daedalus/snapshot" },
        { method: "get", path: "/daedalus/governance/posture" },
        { method: "get", path: "/daedalus/cockpit/nodes" },
        { method: "get", path: "/daedalus/beings/presence" },
        { method: "get", path: "/daedalus/constitution" },
        { method: "post", path: "/daedalus/mirror/join" },
        { method: "post", path: "/daedalus/mirror/heartbeat" },
        { method: "post", path: "/daedalus/governance/overrides" },
        { method: "post", path: "/daedalus/governance/votes" },
        { method: "delete", path: "/daedalus/governance/overrides" },
      ];

      for (const route of routes) {
        const res = await (request(app) as any)[route.method](route.path);
        expect(res.status).toBe(401);
      }
    });

    test("wrong token → 401", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", "wrong-token-attempt");
      expect(res.status).toBe(401);
    });

    test("empty token → 401", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", "");
      expect(res.status).toBe(401);
    });

    test("partial token → 401", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", VALID_TOKEN.substring(0, 5));
      expect(res.status).toBe(401);
    });

    test("Bearer format works when correct", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("Authorization", `Bearer ${VALID_TOKEN}`);
      expect(res.status).toBe(200);
    });

    test("Bearer with wrong token → 401", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("Authorization", "Bearer wrong-token");
      expect(res.status).toBe(401);
    });

    test("query param token works when correct", async () => {
      const res = await request(app)
        .get(`/daedalus/snapshot?token=${VALID_TOKEN}`);
      expect(res.status).toBe(200);
    });

    test("query param with wrong token → 401", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot?token=wrong");
      expect(res.status).toBe(401);
    });

    test("health endpoint is NOT protected", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
    });

    test("case-sensitive header name handling", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("X-Daedalus-Token", VALID_TOKEN);
      // HTTP headers are case-insensitive; Express lowercases them
      expect(res.status).toBe(200);
    });

    test("token in body is ignored (must be header/query)", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .send({ token: VALID_TOKEN, nodeId: "hack-1" });
      expect(res.status).toBe(401);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 2. INJECTION ATTACKS
  // ═══════════════════════════════════════════════════════════════════════
  describe("Injection attacks", () => {
    const auth = () => ({ "x-daedalus-token": VALID_TOKEN });

    test("XSS in node name — stored but not executed (no HTML in JSON)", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "xss-node",
          name: '<script>alert("xss")</script>',
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "xss-node", name: "XSS", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });
      expect([200, 201]).toContain(res.status);

      // Verify it's stored raw, not sanitized (JSON API, not HTML)
      const view = await request(app)
        .get("/daedalus/cockpit/nodes")
        .set(auth());
      const node = view.body.find((n: any) => n.id === "xss-node");
      expect(node?.name).toContain("<script>");
      // This is acceptable for a JSON API but the cockpit must escape it in React
    });

    test("SQL injection in nodeId — no crash", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "'; DROP TABLE nodes; --",
          name: "SQLi Node",
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "sqli", name: "SQLi", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });
      expect([200, 201, 400]).toContain(res.status);
    });

    test("path traversal in node ID — no file access", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "../../../etc/passwd",
          name: "PathTraversal",
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "traversal", name: "PT", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });
      expect([200, 201, 400]).toContain(res.status);
      // Verify no crash and server still responsive
      const health = await request(app).get("/health");
      expect(health.status).toBe(200);
    });

    test("prototype pollution via __proto__ — no effect", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "proto-node",
          name: "Proto",
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "proto-node", name: "Proto", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
          __proto__: { isAdmin: true },
          constructor: { prototype: { isAdmin: true } },
        });
      expect([200, 201, 400]).toContain(res.status);

      // Verify no global pollution
      expect((({} as any).isAdmin)).toBeUndefined();
    });

    test("massive payload — doesn't crash server", async () => {
      const bigString = "A".repeat(1_000_000); // 1MB string
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "big-node",
          name: bigString,
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "big-node", name: bigString, kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });
      // Should either succeed or fail gracefully (possibly 413 or express body limit)
      expect([200, 400, 413]).toContain(res.status);

      // Server still alive
      const health = await request(app).get("/health");
      expect(health.status).toBe(200);
    });

    test("deeply nested JSON — doesn't stack overflow", async () => {
      let nested: any = { value: "bottom" };
      for (let i = 0; i < 100; i++) {
        nested = { child: nested };
      }
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "nested-node",
          name: "Nested",
          capabilities: [nested],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "nested", name: "Nested", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });
      expect([200, 201, 400]).toContain(res.status);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 3. STATE POISONING
  // ═══════════════════════════════════════════════════════════════════════
  describe("State poisoning", () => {
    const auth = () => ({ "x-daedalus-token": VALID_TOKEN });

    test("override with invalid scope — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/governance/overrides")
        .set(auth())
        .send({
          createdBy: { id: "operator", role: "OPERATOR", label: "Op" },
          reason: "hack",
          scope: "INVALID_SCOPE",
          effect: "ALLOW",
        });
      expect(res.status).toBe(400);
    });

    test("override with invalid effect — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/governance/overrides")
        .set(auth())
        .send({
          createdBy: { id: "operator", role: "OPERATOR", label: "Op" },
          reason: "hack",
          scope: "NODE",
          effect: "DESTROY_ALL",
        });
      expect(res.status).toBe(400);
    });

    test("vote with weight > 1 — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/governance/votes")
        .set(auth())
        .send({
          being: { id: "operator", role: "OPERATOR", label: "Op" },
          vote: "ALLOW",
          weight: 999,
        });
      expect(res.status).toBe(400);
    });

    test("vote with negative weight — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/governance/votes")
        .set(auth())
        .send({
          being: { id: "operator", role: "OPERATOR", label: "Op" },
          vote: "ALLOW",
          weight: -1,
        });
      expect(res.status).toBe(400);
    });

    test("drift with invalid severity — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/governance/drifts")
        .set(auth())
        .send({
          severity: "CATASTROPHIC",
          summary: "hack",
        });
      expect(res.status).toBe(400);
    });

    test("join with missing required fields — rejected", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({ nodeId: "incomplete" });
      expect(res.status).toBe(400);
    });

    test("heartbeat for non-existent node — handled gracefully", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/heartbeat")
        .set(auth())
        .send({
          nodeId: "does-not-exist-ever",
          timestamp: new Date().toISOString(),
          status: "alive",
        });
      // Should not crash — either 404 or 200 with no-op
      expect([200, 404]).toContain(res.status);
    });

    test("being update for non-existent being — handled gracefully", async () => {
      const res = await request(app)
        .put("/daedalus/beings/nonexistent-fake/presence")
        .set(auth())
        .send({ influenceLevel: 1.0 });
      // Should create or 404 — not crash
      expect([200, 404]).toContain(res.status);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 4. DATA EXFILTRATION ATTEMPTS
  // ═══════════════════════════════════════════════════════════════════════
  describe("Data exfiltration", () => {
    test("no sensitive data in health endpoint", async () => {
      const res = await request(app).get("/health");
      const body = JSON.stringify(res.body);
      expect(body).not.toContain("token");
      expect(body).not.toContain("secret");
      expect(body).not.toContain("password");
      expect(body).not.toContain(VALID_TOKEN);
    });

    test("error responses don't leak stack traces", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", "wrong");
      expect(res.status).toBe(401);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain("node_modules");
      expect(body).not.toContain("at Object.");
      expect(body).not.toContain(".ts:");
    });

    test("401 response doesn't reveal valid token format", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot");
      expect(res.body.error).toBeDefined();
      expect(res.body.error).not.toContain(VALID_TOKEN);
      expect(res.body.error).not.toContain("daedalus-dev");
    });

    test("unknown routes return 404, not 500 (no internal crash)", async () => {
      const res = await request(app)
        .get("/daedalus/admin/secret")
        .set("x-daedalus-token", VALID_TOKEN);
      // 404 is correct; 500 would indicate an internal error leak
      expect(res.status).not.toBe(500);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain("node_modules");
      expect(body).not.toContain(VALID_TOKEN);
    });

    test("snapshot doesn't contain token or auth data", async () => {
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", VALID_TOKEN);
      expect(res.status).toBe(200);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain(VALID_TOKEN);
      expect(body).not.toContain("password");
      expect(body).not.toContain("secret");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 5. DENIAL-OF-SERVICE / RESOURCE EXHAUSTION
  // ═══════════════════════════════════════════════════════════════════════
  describe("DoS / resource exhaustion", () => {
    const auth = () => ({ "x-daedalus-token": VALID_TOKEN });

    test("100 rapid override creations — server stays responsive", async () => {
      for (let i = 0; i < 100; i++) {
        await request(app)
          .post("/daedalus/governance/overrides")
          .set(auth())
          .send({
            createdBy: { id: "operator", role: "OPERATOR", label: "Op" },
            reason: `spam-${i}`,
            scope: "NODE",
            effect: "ALLOW",
          });
      }

      // Server still responsive
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);

      // Clean up
      await request(app).delete("/daedalus/governance/overrides").set(auth());
    });

    test("50 rapid vote casts — capped at 50", async () => {
      for (let i = 0; i < 55; i++) {
        await request(app)
          .post("/daedalus/governance/votes")
          .set(auth())
          .send({
            being: { id: `spam-being-${i}`, role: "OPERATOR", label: `SB${i}` },
            vote: "ALLOW",
            weight: 0.1,
          });
      }

      const votesRes = await request(app)
        .get("/daedalus/governance/votes")
        .set(auth());
      // Vote cap is 50
      expect(votesRes.body.length).toBeLessThanOrEqual(50);

      // Clean up
      await request(app).delete("/daedalus/governance/votes").set(auth());
    });

    test("rapid heartbeats don't accumulate unbounded memory", async () => {
      // First join a node
      await request(app)
        .post("/daedalus/mirror/join")
        .set(auth())
        .send({
          nodeId: "dos-node",
          name: "DOS",
          capabilities: [],
          expressive: { glow: { level: "low", intensity: 0.5 }, posture: "companion", attention: { level: "aware" }, continuity: "stable" },
          profile: { id: "dos-node", name: "DOS", kind: "server", model: "x", os: "x", osVersion: "x", operatorId: "operator" },
        });

      const before = process.memoryUsage().heapUsed;
      for (let i = 0; i < 1000; i++) {
        await request(app)
          .post("/daedalus/mirror/heartbeat")
          .set(auth())
          .send({ nodeId: "dos-node", timestamp: new Date().toISOString(), status: "alive" });
      }
      const after = process.memoryUsage().heapUsed;
      const growthMB = (after - before) / 1024 / 1024;

      // Should not grow more than 50MB from 1000 heartbeats
      expect(growthMB).toBeLessThan(50);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 6. HEADER MANIPULATION
  // ═══════════════════════════════════════════════════════════════════════
  describe("Header manipulation", () => {
    test("Content-Type: text/plain — still processed (Express json middleware)", async () => {
      const res = await request(app)
        .post("/daedalus/mirror/join")
        .set("x-daedalus-token", VALID_TOKEN)
        .set("Content-Type", "text/plain")
        .send('{"nodeId":"text-node"}');
      // Express json() only parses application/json — should fail gracefully
      expect([200, 400, 415]).toContain(res.status);
    });

    test("very long header value — doesn't crash", async () => {
      const longValue = "X".repeat(10_000);
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", longValue);
      expect(res.status).toBe(401); // Wrong token
    });

    test("null bytes in header — rejected at HTTP layer (Node.js protection)", async () => {
      // Node.js / superagent rejects null bytes at the HTTP layer
      try {
        await request(app)
          .get("/daedalus/snapshot")
          .set("x-daedalus-token", `${VALID_TOKEN}\x00evil`);
        // If it somehow gets through, token won't match → 401
      } catch (err: any) {
        expect(err.message).toContain("Invalid character");
      }
      // Either way, server didn't crash
      const health = await request(app).get("/health");
      expect(health.status).toBe(200);
    });

    test("duplicate auth headers — first wins or consistent behavior", async () => {
      // supertest only sends the last set header with same name
      const res = await request(app)
        .get("/daedalus/snapshot")
        .set("x-daedalus-token", "wrong")
        .set("x-daedalus-token", VALID_TOKEN);
      expect(res.status).toBe(200);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 7. ENDPOINT PROBING
  // ═══════════════════════════════════════════════════════════════════════
  describe("Endpoint probing", () => {
    const auth = () => ({ "x-daedalus-token": VALID_TOKEN });

    test("non-existent subroutes don't crash", async () => {
      const probes = [
        "/daedalus/admin",
        "/daedalus/config",
        "/daedalus/env",
        "/daedalus/debug",
        "/daedalus/../../../etc/passwd",
        "/daedalus/%00",
        "/daedalus/mirror/../../secret",
      ];
      for (const path of probes) {
        const res = await request(app).get(path).set(auth());
        expect(res.status).not.toBe(500);
      }
    });

    test("HTTP methods on wrong endpoints — handled", async () => {
      // DELETE on a GET-only endpoint
      const res1 = await request(app)
        .delete("/daedalus/snapshot")
        .set(auth());
      expect(res1.status).not.toBe(500);

      // PUT on cockpit nodes
      const res2 = await request(app)
        .put("/daedalus/cockpit/nodes")
        .set(auth())
        .send({});
      expect(res2.status).not.toBe(500);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 8. POST-ATTACK INTEGRITY
  // ═══════════════════════════════════════════════════════════════════════
  describe("Post-attack integrity", () => {
    const auth = () => ({ "x-daedalus-token": VALID_TOKEN });

    test("server is still healthy after all attacks", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
    });

    test("governance posture is still valid", async () => {
      const res = await request(app)
        .get("/daedalus/governance/posture")
        .set(auth());
      expect(res.status).toBe(200);
      expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(res.body.posture);
    });

    test("constitution still holds", async () => {
      const res = await request(app)
        .get("/daedalus/constitution")
        .set(auth());
      expect(res.status).toBe(200);
      expect(res.body.allPassed).toBe(true);
    });

    test("beings are intact", async () => {
      const res = await request(app)
        .get("/daedalus/beings/presence")
        .set(auth());
      expect(res.status).toBe(200);
      expect(res.body.find((b: any) => b.id === "operator")).toBeDefined();
    });
  });
});
