import {
  NodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload } from "../orchestrator/mirror";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import {
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

// ─── Helpers ──────────────────────────────────────────────────────────

function mkJoinPayload(id: string): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server",
      model: "test",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function mkHeartbeat(id: string): NodeHeartbeatPayload {
  return { nodeId: id, timestamp: new Date().toISOString(), status: "alive" };
}

// ─── Global Invariant Checker ─────────────────────────────────────────

interface InvariantViolation {
  invariant: string;
  detail: string;
}

function checkGlobalInvariants(
  reg: NodeMirrorRegistry,
  gov: GovernanceService,
): InvariantViolation[] {
  const violations: InvariantViolation[] = [];
  const mirrors = reg.getAllMirrors();

  // --- Node-level invariants ---

  for (const m of mirrors) {
    if (m.lifecycle.phase === "active" && m.status === "quarantined") {
      violations.push({
        invariant: "no-active-and-quarantined",
        detail: `Mirror ${m.id} is active phase but quarantined status`,
      });
    }
    if (m.lifecycle.phase === "quarantined" && m.status !== "quarantined") {
      violations.push({
        invariant: "phase-status-consistency",
        detail: `Mirror ${m.id} phase=quarantined but status=${m.status}`,
      });
    }

    if (m.lifecycle.heartbeatCount < 0) {
      violations.push({
        invariant: "heartbeat-non-negative",
        detail: `Mirror ${m.id} heartbeatCount=${m.lifecycle.heartbeatCount}`,
      });
    }

    if (m.lifecycle.errorCount < 0 || m.lifecycle.errorCount >= 10_000) {
      violations.push({
        invariant: "error-count-bounded",
        detail: `Mirror ${m.id} errorCount=${m.lifecycle.errorCount}`,
      });
    }

    if (
      m.lifecycle.lastHeartbeat !== null &&
      isNaN(Date.parse(m.lifecycle.lastHeartbeat))
    ) {
      violations.push({
        invariant: "valid-heartbeat-timestamp",
        detail: `Mirror ${m.id} lastHeartbeat="${m.lifecycle.lastHeartbeat}" is invalid`,
      });
    }
  }

  // --- Governance-level invariants ---

  const snapshot = gov.getPostureSnapshot();
  const overrides = gov.listOverrides();
  const drifts = gov.listDrifts();
  const votes = gov.listVotes();

  if (snapshot.activeOverrides.length !== overrides.length) {
    violations.push({
      invariant: "posture-overrides-match",
      detail: `snapshot.activeOverrides(${snapshot.activeOverrides.length}) != overrides(${overrides.length})`,
    });
  }

  if (snapshot.activeDrifts.length !== drifts.length) {
    violations.push({
      invariant: "posture-drifts-match",
      detail: `snapshot.activeDrifts(${snapshot.activeDrifts.length}) != drifts(${drifts.length})`,
    });
  }

  const validScopes = ["NODE", "CAPABILITY", "GLOBAL"];
  const validEffects = ["ALLOW", "DENY", "ESCALATE"];
  for (const o of overrides) {
    if (!validScopes.includes(o.scope)) {
      violations.push({
        invariant: "valid-override-scope",
        detail: `Override ${o.id} has invalid scope "${o.scope}"`,
      });
    }
    if (!validEffects.includes(o.effect)) {
      violations.push({
        invariant: "valid-override-effect",
        detail: `Override ${o.id} has invalid effect "${o.effect}"`,
      });
    }
  }

  for (const v of votes) {
    if (v.weight < 0 || v.weight > 1) {
      violations.push({
        invariant: "vote-weight-bounded",
        detail: `Vote by ${v.being.id} has weight ${v.weight}`,
      });
    }
  }

  const validPostures = ["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"];
  if (!validPostures.includes(snapshot.posture)) {
    violations.push({
      invariant: "valid-posture-value",
      detail: `Posture "${snapshot.posture}" is not valid`,
    });
  }

  // --- Continuity-level invariants ---

  const beings = daedalusStore.getBeingPresences();
  for (const b of beings) {
    if (b.continuity.streak < 0) {
      violations.push({
        invariant: "continuity-streak-non-negative",
        detail: `Being ${b.id} has streak ${b.continuity.streak}`,
      });
    }
    if (b.influenceLevel < 0) {
      violations.push({
        invariant: "influence-non-negative",
        detail: `Being ${b.id} has influenceLevel ${b.influenceLevel}`,
      });
    }
  }

  const beingMap: Record<string, BeingPresenceDetail> = {};
  for (const b of beings) beingMap[b.id] = b;
  const behavioral = computeBehavioralField(beingMap);
  if (
    behavioral.dominantBeingId !== null &&
    !beings.some((b) => b.id === behavioral.dominantBeingId)
  ) {
    violations.push({
      invariant: "anchor-being-exists",
      detail: `anchorBeingId "${behavioral.dominantBeingId}" not found in beings`,
    });
  }

  // --- Being-level invariants ---

  const seenIds = new Set<string>();
  for (const b of beings) {
    if (!b.id || !b.name || !b.posture) {
      violations.push({
        invariant: "being-required-fields",
        detail: `Being missing id/name/posture: ${JSON.stringify({ id: b.id, name: b.name, posture: b.posture })}`,
      });
    }
    if (seenIds.has(b.id)) {
      violations.push({
        invariant: "no-duplicate-being-ids",
        detail: `Duplicate being id "${b.id}"`,
      });
    }
    seenIds.add(b.id);
  }

  if (!beings.some((b) => b.id === "operator")) {
    violations.push({
      invariant: "operator-always-present",
      detail: "Operator being missing from seed",
    });
  }

  return violations;
}

// ─── Tests ────────────────────────────────────────────────────────────

describe("Global invariants", () => {
  let reg: NodeMirrorRegistry;
  let gov: GovernanceService;

  beforeEach(() => {
    resetDaedalusEventBus();
    reg = new NodeMirrorRegistry();
    gov = new GovernanceService();
  });

  test("invariants hold on fresh start", () => {
    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold after 50 joins + 20 heartbeats", () => {
    for (let i = 0; i < 50; i++) {
      reg.handleJoin(mkJoinPayload(`node-${i}`));
    }
    for (let i = 0; i < 20; i++) {
      reg.handleHeartbeat(mkHeartbeat(`node-${i}`));
    }

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold after governance storm (10 overrides, 10 drifts, 10 votes)", () => {
    for (let i = 0; i < 10; i++) {
      gov.applyOverride({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: `Override ${i}`,
        scope: "NODE",
        targetId: `n${i}`,
        effect: "ALLOW",
      });
    }
    for (let i = 0; i < 10; i++) {
      const severity = i < 3 ? "HIGH" : i < 6 ? "MEDIUM" : "LOW";
      gov.recordDrift({
        severity: severity as "HIGH" | "MEDIUM" | "LOW",
        summary: `Drift ${i}`,
      });
    }
    for (let i = 0; i < 10; i++) {
      gov.castVote({
        being: { id: `being-${i}`, role: "GUARDIAN", label: `Guardian ${i}` },
        vote: "ALLOW",
        weight: 0.5,
      });
    }

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold after error cascade + auto-quarantine", () => {
    reg.configureSafety({ errorQuarantineThreshold: 3 });
    reg.handleJoin(mkJoinPayload("err-node"));

    for (let i = 0; i < 5; i++) {
      reg.handleError("err-node", `Error ${i}`);
    }

    const mirror = reg.getMirror("err-node")!;
    expect(mirror.lifecycle.phase).toBe("quarantined");

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold after full detach cycle", () => {
    reg.handleJoin(mkJoinPayload("detach-node"));
    reg.handleHeartbeat(mkHeartbeat("detach-node"));
    reg.handleQuarantine("detach-node");
    reg.handleDetach("detach-node");

    expect(reg.getMirror("detach-node")).toBeUndefined();

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold after rapid join/leave/rejoin", () => {
    for (let cycle = 0; cycle < 10; cycle++) {
      reg.handleJoin(mkJoinPayload("churn-node"));
      reg.handleHeartbeat(mkHeartbeat("churn-node"));
      reg.handleDetach("churn-node");
    }
    reg.handleJoin(mkJoinPayload("churn-node"));

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
  });

  test("invariants hold under maximal load (200 nodes, 50 overrides, 50 votes)", () => {
    for (let i = 0; i < 200; i++) {
      reg.handleJoin(mkJoinPayload(`load-${i}`));
    }
    for (let i = 0; i < 100; i++) {
      reg.handleHeartbeat(mkHeartbeat(`load-${i}`));
    }

    for (let i = 0; i < 50; i++) {
      gov.applyOverride({
        createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
        reason: `Load override ${i}`,
        scope: "NODE",
        targetId: `load-${i}`,
        effect: i % 3 === 0 ? "DENY" : "ALLOW",
      });
    }
    for (let i = 0; i < 50; i++) {
      gov.castVote({
        being: { id: `voter-${i}`, role: "SENTINEL", label: `Sentinel ${i}` },
        vote: "ALLOW",
        weight: Math.min(1, 0.02 * i),
      });
    }

    const violations = checkGlobalInvariants(reg, gov);
    expect(violations).toEqual([]);
    expect(reg.getCount()).toBe(200);
  });
});
