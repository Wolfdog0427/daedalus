/**
 * OPERATOR BAD DAY — Scripted Stress Scenario
 *
 * Simulates a realistic "bad day" for an operator: cascading failures,
 * confusing states, time pressure, and the need to make decisions.
 *
 * For each phase, we validate not just "does it work?" but:
 *   - Is the current state obvious from the cockpit endpoints?
 *   - Can the operator tell what to do next?
 *   - Are there any confusing or ambiguous signals?
 *
 * This test documents every cockpit response so we can assess UX clarity.
 */

import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  NodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import { IDLE_EXPRESSIVE } from "../orchestrator/mirror/NodeMirror.types";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";

jest.setTimeout(60_000);

function mkJoin(id: string) {
  return {
    nodeId: id,
    name: `Node-${id}`,
    capabilities: [
      { name: "core", value: "enabled", enabled: true },
      { name: "heartbeat", value: "enabled", enabled: true },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: {
      id,
      name: `Node-${id}`,
      kind: "server" as const,
      model: "prod",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
  };
}

function mkHb(nodeId: string, status: "alive" | "degraded" = "alive") {
  return { nodeId, timestamp: new Date().toISOString(), status };
}

interface UXSnapshot {
  phase: string;
  summary: any;
  posture: any;
  nodeCount: number;
  quarantinedNodes: string[];
  degradedNodes: string[];
  activeOverrides: number;
  activeDrifts: number;
  constitutionPassed: boolean;
  uxQuestions: string[];
}

describe("OPERATOR BAD DAY — Scripted Stress Scenario", () => {
  const app = createOrchestratorApp();
  let reg: NodeMirrorRegistry;
  const events: DaedalusEventPayload[] = [];
  let unsub: (() => void) | null = null;
  const uxLog: UXSnapshot[] = [];

  async function captureUX(phase: string, questions: string[]): Promise<UXSnapshot> {
    const [summaryRes, postureRes, nodesRes, constRes] = await Promise.all([
      request(app).get("/daedalus/cockpit/summary"),
      request(app).get("/daedalus/governance/posture"),
      request(app).get("/daedalus/cockpit/nodes"),
      request(app).get("/daedalus/constitution"),
    ]);

    const nodes = nodesRes.body as any[];
    const snap: UXSnapshot = {
      phase,
      summary: summaryRes.body,
      posture: postureRes.body.posture,
      nodeCount: nodes.length,
      quarantinedNodes: nodes.filter(n => n.status === "quarantined").map(n => n.id),
      degradedNodes: nodes.filter(n => n.phase === "degraded").map(n => n.id),
      activeOverrides: postureRes.body.activeOverrides?.length ?? 0,
      activeDrifts: postureRes.body.activeDrifts?.length ?? 0,
      constitutionPassed: constRes.body.allPassed,
      uxQuestions: questions,
    };
    uxLog.push(snap);
    return snap;
  }

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    reg = getNodeMirrorRegistry();

    unsub = getDaedalusEventBus().subscribe(e => events.push(e));
  });

  afterAll(() => {
    unsub?.();
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 1: Morning — Everything is fine
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 1: Calm morning — 10 healthy nodes, posture OPEN", async () => {
    for (let i = 1; i <= 10; i++) {
      reg.handleJoin(mkJoin(`prod-${i}`));
      reg.handleHeartbeat(mkHb(`prod-${i}`));
    }

    const ux = await captureUX("Morning: all clear", [
      "Can operator see all 10 nodes?",
      "Is posture clearly OPEN?",
      "Any confusing signals?",
    ]);

    expect(ux.nodeCount).toBe(10);
    expect(ux.posture).toBe("OPEN");
    expect(ux.quarantinedNodes).toHaveLength(0);
    expect(ux.degradedNodes).toHaveLength(0);
    expect(ux.constitutionPassed).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 2: First sign of trouble — one node starts degrading
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 2: First trouble — node prod-3 sends degraded heartbeats", async () => {
    for (let i = 0; i < 3; i++) {
      reg.handleHeartbeat(mkHb("prod-3", "degraded"));
    }

    const ux = await captureUX("First trouble: prod-3 degraded", [
      "Can operator see prod-3 is degraded?",
      "Is there a clear signal that ONE node is problematic?",
      "Does the overall posture change (should it)?",
    ]);

    expect(ux.degradedNodes).toContain("prod-3");
    expect(ux.posture).toBe("OPEN"); // One degraded node shouldn't change global posture
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 3: Cascade — 3 nodes start erroring
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 3: Cascade — prod-3, prod-4, prod-5 accumulate errors", async () => {
    for (const id of ["prod-3", "prod-4", "prod-5"]) {
      for (let e = 0; e < 4; e++) {
        reg.handleError(id, `Connection timeout to database`);
      }
    }

    const ux = await captureUX("Cascade: 3 nodes erroring", [
      "Can operator see error counts on the 3 nodes?",
      "Is there a clear 'these are the problem nodes' signal?",
      "Should operator intervene or wait?",
    ]);

    // 3 nodes have 4 errors each — not yet quarantined (threshold is 5)
    expect(ux.quarantinedNodes).toHaveLength(0);
    expect(ux.summary.totalErrors).toBeGreaterThanOrEqual(12);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 4: Auto-quarantine fires — 2 nodes hit threshold
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 4: Auto-quarantine — prod-3 and prod-4 hit error threshold", async () => {
    reg.handleError("prod-3", "Final error");
    reg.handleError("prod-4", "Final error");

    const ux = await captureUX("Auto-quarantine fires", [
      "Can operator see quarantined nodes clearly?",
      "Is it obvious WHY they were quarantined (error count)?",
      "Does posture change? Should it?",
    ]);

    expect(ux.quarantinedNodes).toContain("prod-3");
    expect(ux.quarantinedNodes).toContain("prod-4");
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 5: Governance escalation — operator notices and adds override
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 5: Operator intervenes — adds GUARDED override + drift", async () => {
    governanceService.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR" as const, label: "Operator" },
      reason: "Multiple node failures — investigating",
      scope: "GLOBAL" as const,
      effect: "ESCALATE" as const,
    });
    governanceService.recordDrift({
      severity: "HIGH" as const,
      summary: "Cascading node failures detected",
    });

    const ux = await captureUX("Operator escalates governance", [
      "Is the posture change visible and clear?",
      "Can operator see their own override?",
      "Is the drift visible?",
      "Does the cockpit feel 'tense' — matching the situation?",
    ]);

    // GLOBAL ESCALATE + HIGH drift → at least GUARDED (LOCKDOWN requires GLOBAL DENY)
    expect(["GUARDED", "LOCKDOWN"]).toContain(ux.posture);
    expect(ux.activeOverrides).toBeGreaterThanOrEqual(1);
    expect(ux.activeDrifts).toBeGreaterThanOrEqual(1);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 6: More trouble — a node goes completely silent
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 6: Silent node — prod-7 goes silent (stale sweep)", async () => {
    // Simulate stale heartbeat by sweeping with a far-future timestamp
    const farFuture = Date.now() + 120_000;
    const stale = reg.sweepStaleHeartbeats(farFuture);

    const ux = await captureUX("Node goes silent after stale sweep", [
      "Can operator see which nodes were marked stale?",
      "Is there a difference between 'errored' and 'silent'?",
      "Is the situation clearly worsening?",
    ]);

    // Multiple nodes should be marked stale
    expect(stale.length).toBeGreaterThan(0);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 7: Operator takes manual action — quarantines prod-5
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 7: Manual quarantine — operator quarantines prod-5", async () => {
    const m = reg.getMirror("prod-5");
    if (m && m.lifecycle.phase !== "quarantined" && m.lifecycle.phase !== "detached") {
      reg.handleQuarantine("prod-5");
    }

    const ux = await captureUX("Manual quarantine of prod-5", [
      "Can operator confirm prod-5 is now quarantined?",
      "Does the quarantine count update in summary?",
      "Is there a clear way to UNDO this if it was a mistake?",
    ]);

    expect(ux.quarantinedNodes).toContain("prod-5");
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 8: Recovery begins — fix the root cause, detach and rejoin nodes
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 8: Recovery — detach quarantined nodes and rejoin", async () => {
    const quarantined = reg.getAllMirrors().filter(m => m.lifecycle.phase === "quarantined");
    for (const m of quarantined) {
      reg.handleDetach(m.id);
      reg.handleJoin(mkJoin(m.id));
      reg.handleHeartbeat(mkHb(m.id));
    }

    // Send healthy heartbeats for remaining active nodes
    const active = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active" || m.lifecycle.phase === "degraded");
    for (const m of active) {
      reg.handleHeartbeat(mkHb(m.id));
    }

    const ux = await captureUX("Nodes rejoined and recovering", [
      "Can operator see recovered nodes?",
      "Do they show as 'active' again?",
      "Is the situation clearly improving?",
    ]);

    expect(ux.quarantinedNodes).toHaveLength(0);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 9: Operator de-escalates — clears overrides and drifts
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 9: De-escalation — clear overrides and drifts", async () => {
    governanceService.clearOverrides();
    governanceService.clearDrifts();

    const ux = await captureUX("Overrides and drifts cleared", [
      "Does posture return to OPEN?",
      "Is it clear that the incident is resolved?",
      "Is there any 'residue' from the incident?",
    ]);

    expect(ux.posture).toBe("OPEN");
    expect(ux.activeOverrides).toBe(0);
    expect(ux.activeDrifts).toBe(0);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ACT 10: End of day — everything stable
  // ═══════════════════════════════════════════════════════════════════════
  test("Act 10: End of day — system stable, constitution holds", async () => {
    const ux = await captureUX("End of day: stable", [
      "Is the system clearly healthy?",
      "Would an operator feel confident leaving for the night?",
      "Any lingering concerns?",
    ]);

    expect(ux.constitutionPassed).toBe(true);
    expect(ux.posture).toBe("OPEN");
    expect(ux.quarantinedNodes).toHaveLength(0);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // UX ANALYSIS — Document what the operator would see at each step
  // ═══════════════════════════════════════════════════════════════════════
  test("UX Analysis: Generate operator experience report", () => {
    const report = [
      "",
      "╔══════════════════════════════════════════════════════════════╗",
      "║         OPERATOR BAD DAY — UX ANALYSIS REPORT               ║",
      "╚══════════════════════════════════════════════════════════════╝",
      "",
    ];

    for (const snap of uxLog) {
      report.push(`┌── ${snap.phase} ──────────────────────────────────────`);
      report.push(`│  Posture: ${snap.posture}`);
      report.push(`│  Nodes: ${snap.nodeCount} total, ${snap.quarantinedNodes.length} quarantined, ${snap.degradedNodes.length} degraded`);
      report.push(`│  Overrides: ${snap.activeOverrides}, Drifts: ${snap.activeDrifts}`);
      report.push(`│  Constitution: ${snap.constitutionPassed ? "PASSED" : "FAILED"}`);
      report.push(`│  Summary: ${JSON.stringify(snap.summary)}`);
      report.push("│");
      report.push("│  UX Questions:");
      for (const q of snap.uxQuestions) {
        report.push(`│    ? ${q}`);
      }
      report.push("└─────────────────────────────────────────────────────────");
      report.push("");
    }

    // UX Findings
    report.push("┌── UX FINDINGS ─────────────────────────────────────────────");

    // Check: does summary always have node counts?
    const allSummaries = uxLog.map(u => u.summary);
    const hasTotalNodes = allSummaries.every(s => typeof s.totalNodes === "number");
    report.push(`│  Summary always has totalNodes: ${hasTotalNodes ? "YES" : "NO — ISSUE"}`);

    // Check: does summary break down by status?
    const hasByStatus = allSummaries.every(s => s.byStatus && typeof s.byStatus === "object");
    report.push(`│  Summary always has byStatus: ${hasByStatus ? "YES" : "NO — ISSUE"}`);

    // Check: urgency and recommended actions are present
    const hasUrgency = allSummaries.every(s => typeof s.urgency === "string");
    report.push(`│  Summary always has urgency: ${hasUrgency ? "YES" : "NO — ISSUE"}`);
    const hasActions = allSummaries.every(s => Array.isArray(s.recommendedActions));
    report.push(`│  Summary always has recommendedActions: ${hasActions ? "YES" : "NO — ISSUE"}`);
    const hasPosture = allSummaries.every(s => typeof s.posture === "string");
    report.push(`│  Summary always has posture: ${hasPosture ? "YES" : "NO — ISSUE"}`);

    report.push("│");
    report.push("│  RESOLVED:");
    report.push("│  ✓ 'urgency' indicator now present in cockpit summary");
    report.push("│  ✓ 'recommendedActions' array now present in cockpit summary");
    report.push("│  ✓ Posture and reason now present in cockpit summary");
    report.push("│");
    report.push("│  REMAINING GAPS:");
    report.push("│  1. No event history / timeline in cockpit (must check events separately)");
    report.push("│  2. Error counts visible per-node but no aggregate 'error rate'");
    report.push("│  3. No 'incident' concept — operator can't mark start/end of incident");
    report.push("│  4. No 'undo last action' button — must manually reverse");
    report.push("└─────────────────────────────────────────────────────────");

    console.log(report.join("\n"));

    // The fact that we can capture all this data means the system is functional
    expect(uxLog.length).toBeGreaterThanOrEqual(8);
    expect(uxLog.every(u => u.constitutionPassed)).toBe(true);
  });
});
