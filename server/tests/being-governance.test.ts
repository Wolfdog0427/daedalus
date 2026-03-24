/**
 * Phase 4 — Governance–Being Integration Audit
 *
 * Validates: BeingVote posture influence, BeingIdFull on overrides,
 * vote-weighted posture escalation, vote clearing, and interaction
 * between votes + overrides + drifts.
 */

import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { resetDaedalusEventBus, getDaedalusEventBus, DaedalusEventPayload } from "../orchestrator/DaedalusEventBus";
import type { BeingIdFull, BeingVote } from "../../shared/daedalus/contracts";
import { ROLE_DESCRIPTORS } from "../../shared/daedalus/beingOntology";

function mkBeing(role: "OPERATOR" | "GUARDIAN" | "SENTINEL" = "OPERATOR"): BeingIdFull {
  const desc = ROLE_DESCRIPTORS[role];
  return { id: desc.role.toLowerCase(), role, label: desc.label };
}

function mkVote(vote: "ALLOW" | "DENY" | "ESCALATE", weight: number, role: "OPERATOR" | "GUARDIAN" | "SENTINEL" = "OPERATOR"): BeingVote {
  return { being: mkBeing(role), vote, weight };
}

// ─── BeingIdFull on Overrides ────────────────────────────────────────

describe("BeingIdFull on governance overrides", () => {
  let service: GovernanceService;
  beforeEach(() => {
    resetDaedalusEventBus();
    service = new GovernanceService();
  });

  test("override createdBy carries full being identity", () => {
    const override = service.applyOverride({
      createdBy: mkBeing("OPERATOR"),
      reason: "Test override",
      scope: "GLOBAL",
      effect: "ALLOW",
    });

    expect(override.createdBy.id).toBe("operator");
    expect(override.createdBy.role).toBe("OPERATOR");
    expect(override.createdBy.label).toBe("Operator");
  });

  test("override attribution is visible in posture snapshot", () => {
    service.applyOverride({
      createdBy: mkBeing("GUARDIAN"),
      reason: "Guardian override",
      scope: "NODE",
      targetId: "n1",
      effect: "ALLOW",
    });

    const snapshot = service.getPostureSnapshot();
    expect(snapshot.activeOverrides).toHaveLength(1);
    expect(snapshot.activeOverrides[0].createdBy.role).toBe("GUARDIAN");
  });
});

// ─── BeingVote Posture Influence ─────────────────────────────────────

describe("BeingVote posture influence", () => {
  let service: GovernanceService;
  beforeEach(() => {
    resetDaedalusEventBus();
    service = new GovernanceService();
  });

  test("initial state with no votes is OPEN", () => {
    expect(service.getPostureSnapshot().posture).toBe("OPEN");
  });

  test("single ALLOW vote moves to ATTENTIVE (votes present)", () => {
    service.castVote(mkVote("ALLOW", 1.0));
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  test("majority DENY vote weight triggers LOCKDOWN", () => {
    service.castVote(mkVote("DENY", 0.8, "OPERATOR"));
    service.castVote(mkVote("ALLOW", 0.2, "GUARDIAN"));
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");
    expect(service.getPostureSnapshot().reason).toContain("DENY");
  });

  test("majority ESCALATE vote weight triggers GUARDED", () => {
    service.castVote(mkVote("ESCALATE", 0.7, "OPERATOR"));
    service.castVote(mkVote("ALLOW", 0.3, "GUARDIAN"));
    expect(service.getPostureSnapshot().posture).toBe("GUARDED");
    expect(service.getPostureSnapshot().reason).toContain("ESCALATE");
  });

  test("equal DENY and ALLOW keeps DENY below majority → ATTENTIVE", () => {
    service.castVote(mkVote("DENY", 0.5, "OPERATOR"));
    service.castVote(mkVote("ALLOW", 0.5, "GUARDIAN"));
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });

  test("new vote from same being replaces old vote", () => {
    service.castVote(mkVote("DENY", 1.0, "OPERATOR"));
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");

    service.castVote(mkVote("ALLOW", 1.0, "OPERATOR"));
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
    expect(service.listVotes()).toHaveLength(1);
  });

  test("clearVotes resets posture back to OPEN", () => {
    service.castVote(mkVote("DENY", 1.0));
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");

    service.clearVotes();
    expect(service.getPostureSnapshot().posture).toBe("OPEN");
    expect(service.listVotes()).toHaveLength(0);
  });

  test("vote emits event with beings array", () => {
    const events: DaedalusEventPayload[] = [];
    getDaedalusEventBus().subscribe(e => events.push(e));

    service.castVote(mkVote("ESCALATE", 0.9));
    const voteEvents = events.filter(e => e.beings && e.beings.length > 0);
    expect(voteEvents.length).toBeGreaterThanOrEqual(1);
    expect(voteEvents[0].beings![0].vote).toBe("ESCALATE");
  });
});

// ─── Vote + Override + Drift Interaction ─────────────────────────────

describe("Vote + Override + Drift interaction", () => {
  let service: GovernanceService;
  beforeEach(() => {
    resetDaedalusEventBus();
    service = new GovernanceService();
  });

  test("global DENY override overrides ALLOW votes", () => {
    service.castVote(mkVote("ALLOW", 1.0, "OPERATOR"));
    service.applyOverride({
      createdBy: mkBeing("OPERATOR"),
      reason: "Emergency",
      scope: "GLOBAL",
      effect: "DENY",
    });
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("HIGH severity drift overrides ALLOW votes", () => {
    service.castVote(mkVote("ALLOW", 1.0, "OPERATOR"));
    service.recordDrift({ severity: "HIGH", summary: "Critical drift" });
    expect(service.getPostureSnapshot().posture).toBe("GUARDED");
  });

  test("DENY vote + HIGH drift → LOCKDOWN (DENY takes priority)", () => {
    service.castVote(mkVote("DENY", 1.0, "OPERATOR"));
    service.recordDrift({ severity: "HIGH", summary: "Critical drift" });
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");
  });

  test("ESCALATE vote + MEDIUM drift → GUARDED (ESCALATE > ATTENTIVE)", () => {
    service.castVote(mkVote("ESCALATE", 1.0, "OPERATOR"));
    service.recordDrift({ severity: "MEDIUM", summary: "Minor drift" });
    expect(service.getPostureSnapshot().posture).toBe("GUARDED");
  });

  test("clearing votes with remaining drift keeps appropriate posture", () => {
    service.castVote(mkVote("DENY", 1.0));
    service.recordDrift({ severity: "MEDIUM", summary: "Medium drift" });
    expect(service.getPostureSnapshot().posture).toBe("LOCKDOWN");

    service.clearVotes();
    expect(service.getPostureSnapshot().posture).toBe("ATTENTIVE");
  });
});

// ─── Vote HTTP Routes ────────────────────────────────────────────────

describe("Vote HTTP routes", () => {
  let app: any;
  let request: any;

  beforeAll(async () => {
    const supertest = await import("supertest");
    const { createOrchestratorApp } = await import("../orchestrator/index");
    app = createOrchestratorApp();
    request = supertest.default(app);
  });

  test("GET /daedalus/governance/votes returns array", async () => {
    const res = await request.get("/daedalus/governance/votes").expect(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  test("POST /daedalus/governance/votes creates a vote", async () => {
    const res = await request.post("/daedalus/governance/votes")
      .send(mkVote("ALLOW", 0.5, "GUARDIAN"))
      .expect(201);
    expect(res.body.vote).toBe("ALLOW");
    expect(res.body.being.role).toBe("GUARDIAN");
  });

  test("DELETE /daedalus/governance/votes clears all votes", async () => {
    await request.post("/daedalus/governance/votes")
      .send(mkVote("DENY", 1.0))
      .expect(201);

    await request.delete("/daedalus/governance/votes").expect(204);

    const res = await request.get("/daedalus/governance/votes").expect(200);
    expect(res.body).toHaveLength(0);
  });
});

// ─── Role Permission Validation ──────────────────────────────────────

describe("Role permission validation (ontology consistency)", () => {
  test("OPERATOR can override", () => {
    expect(ROLE_DESCRIPTORS.OPERATOR.canOverride).toBe(true);
  });

  test("GUARDIAN cannot override", () => {
    expect(ROLE_DESCRIPTORS.GUARDIAN.canOverride).toBe(false);
  });

  test("all roles can vote", () => {
    expect(ROLE_DESCRIPTORS.OPERATOR.canVote).toBe(true);
    expect(ROLE_DESCRIPTORS.GUARDIAN.canVote).toBe(true);
    expect(ROLE_DESCRIPTORS.SENTINEL.canVote).toBe(true);
  });
});
