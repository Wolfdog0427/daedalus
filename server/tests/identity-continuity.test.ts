/**
 * Identity & Continuity Check — validates that Daedalus will wake
 * as himself: correct identity anchor, stable continuity baseline,
 * aligned glow/posture/attention across all subsystems.
 */

import {
  DAEDALUS_IDENTITY,
  DAEDALUS_NAME,
  DAEDALUS_SIGIL,
  CANONICAL_OPERATOR_ID,
  CANONICAL_ANCHOR_BEING_ID,
  POSTURE_ARCHETYPES,
  CROWN_GATE,
  FABRIC_GATE,
} from "../../shared/daedalus/identity";

import {
  GLOW_PALETTE,
  POSTURE_GLOW_OVERRIDES,
  glowLevelToHex,
} from "../../shared/daedalus/glowPalette";

import { IDLE_EXPRESSIVE, IDLE_LIFECYCLE } from "../orchestrator/mirror/NodeMirror.types";
import { IDLE_AGENT_EXPRESSIVE } from "../../node-agent/src/NodeAgent.expressive";
import { DEFAULT_AGENT_CONFIG } from "../../node-agent/src/NodeAgent.config";
import { SYSTEM_CONTINUITY_IDLE } from "../../shared/daedalus/systemContinuity";
import { EMBODIED_IDLE } from "../../shared/daedalus/embodiedPresence";
import { CROWN_IDLE } from "../../shared/daedalus/kernelCrown";
import { THRONE_IDLE } from "../../shared/daedalus/kernelThrone";
import { OPERATOR_CONTEXT_IDLE } from "../../shared/daedalus/operatorContext";
import { createFreshMirror } from "../orchestrator/mirror/NodeMirror.lifecycle";

import {
  nodePostureToDaedalusPosture,
  daedalusPostureToNodePosture,
} from "../../shared/daedalus/nodePhysiologyEngine";

// ─── 1.1 Identity Anchor ─────────────────────────────────────────────

describe("Identity Anchor", () => {
  test("name is Daedalus", () => {
    expect(DAEDALUS_NAME).toBe("Daedalus");
    expect(DAEDALUS_IDENTITY.name).toBe("Daedalus");
  });

  test("sigil is the labyrinth", () => {
    expect(DAEDALUS_SIGIL).toBe("labyrinth");
    expect(DAEDALUS_IDENTITY.sigil).toBe("labyrinth");
  });

  test("gates: top (Crown Gate) + bottom (Fabric Gate)", () => {
    expect(DAEDALUS_IDENTITY.gates).toHaveLength(2);

    expect(CROWN_GATE.position).toBe("top");
    expect(CROWN_GATE.name).toBe("Crown Gate");

    expect(FABRIC_GATE.position).toBe("bottom");
    expect(FABRIC_GATE.name).toBe("Fabric Gate");
  });

  test("posture archetypes are the canonical four", () => {
    expect(POSTURE_ARCHETYPES).toEqual(["sentinel", "companion", "observer", "dormant"]);
    expect(DAEDALUS_IDENTITY.postures).toEqual(POSTURE_ARCHETYPES);
  });

  test("canonical operator ID is set and non-empty", () => {
    expect(CANONICAL_OPERATOR_ID).toBe("operator");
    expect(DAEDALUS_IDENTITY.operatorId).toBe("operator");
  });

  test("canonical anchor being ID matches operator", () => {
    expect(CANONICAL_ANCHOR_BEING_ID).toBe("operator");
    expect(DAEDALUS_IDENTITY.anchorBeingId).toBe("operator");
  });

  test("identity is frozen", () => {
    expect(Object.isFrozen(DAEDALUS_IDENTITY)).toBe(true);
    expect(Object.isFrozen(CROWN_GATE)).toBe(true);
    expect(Object.isFrozen(FABRIC_GATE)).toBe(true);
  });
});

// ─── Color Field (Glow Palette) ──────────────────────────────────────

describe("Color Field", () => {
  test("all four glow levels have hex colors", () => {
    expect(glowLevelToHex("none")).toMatch(/^#/);
    expect(glowLevelToHex("low")).toMatch(/^#/);
    expect(glowLevelToHex("medium")).toMatch(/^#/);
    expect(glowLevelToHex("high")).toMatch(/^#/);
  });

  test("glow levels are ordered by brightness", () => {
    expect(GLOW_PALETTE.none.hex).not.toBe(GLOW_PALETTE.high.hex);
  });

  test("posture glow overrides cover all four archetypes", () => {
    for (const posture of POSTURE_ARCHETYPES) {
      expect(POSTURE_GLOW_OVERRIDES[posture]).toBeDefined();
      expect(POSTURE_GLOW_OVERRIDES[posture].hex).toMatch(/^#/);
    }
  });

  test("palette is frozen", () => {
    expect(Object.isFrozen(GLOW_PALETTE)).toBe(true);
  });
});

// ─── 1.2 Continuity Baselines ────────────────────────────────────────

describe("Continuity Baseline", () => {
  test("server IDLE_EXPRESSIVE continuity is healthy", () => {
    expect(IDLE_EXPRESSIVE.continuity.healthy).toBe(true);
    expect(IDLE_EXPRESSIVE.continuity.streak).toBe(0);
  });

  test("agent IDLE_AGENT_EXPRESSIVE continuity is healthy", () => {
    expect(IDLE_AGENT_EXPRESSIVE.continuity.healthy).toBe(true);
    expect(IDLE_AGENT_EXPRESSIVE.continuity.streak).toBe(0);
  });

  test("server and agent idle expressive states agree", () => {
    expect(IDLE_EXPRESSIVE.glow.level).toBe(IDLE_AGENT_EXPRESSIVE.glow.level);
    expect(IDLE_EXPRESSIVE.glow.intensity).toBe(IDLE_AGENT_EXPRESSIVE.glow.intensity);
    expect(IDLE_EXPRESSIVE.posture).toBe(IDLE_AGENT_EXPRESSIVE.posture);
    expect(IDLE_EXPRESSIVE.attention.level).toBe(IDLE_AGENT_EXPRESSIVE.attention.level);
    expect(IDLE_EXPRESSIVE.continuity.healthy).toBe(IDLE_AGENT_EXPRESSIVE.continuity.healthy);
  });

  test("SYSTEM_CONTINUITY_IDLE is healthy with anchor set", () => {
    expect(SYSTEM_CONTINUITY_IDLE.health).toBe("healthy");
    expect(SYSTEM_CONTINUITY_IDLE.composite).toBe(1);
    expect(SYSTEM_CONTINUITY_IDLE.anchorBeingId).toBe(CANONICAL_ANCHOR_BEING_ID);
    expect(SYSTEM_CONTINUITY_IDLE.driftSignalCount).toBe(0);
  });

  test("EMBODIED_IDLE posture matches canonical initial posture", () => {
    expect(EMBODIED_IDLE.posture).toBe("observer");
    expect(IDLE_EXPRESSIVE.posture).toBe("observer");
  });
});

// ─── Glow Baseline ───────────────────────────────────────────────────

describe("Glow Baseline", () => {
  test("initial glow is medium at 0.5 intensity (calm presence)", () => {
    expect(IDLE_EXPRESSIVE.glow.level).toBe("medium");
    expect(IDLE_EXPRESSIVE.glow.intensity).toBe(0.5);
  });

  test("Crown idle glow is 0.3 (governance layer is quieter)", () => {
    expect(CROWN_IDLE.glow).toBe(0.3);
    expect(THRONE_IDLE.glow).toBe(0.3);
  });

  test("glow baseline has a hex color in the palette", () => {
    const hex = glowLevelToHex(IDLE_EXPRESSIVE.glow.level);
    expect(hex).toBe(GLOW_PALETTE.medium.hex);
  });
});

// ─── Posture Baseline ────────────────────────────────────────────────

describe("Posture Baseline", () => {
  test("initial posture is observer across all subsystems", () => {
    expect(IDLE_EXPRESSIVE.posture).toBe("observer");
    expect(IDLE_AGENT_EXPRESSIVE.posture).toBe("observer");
    expect(EMBODIED_IDLE.posture).toBe("observer");
  });

  test("observer is one of the canonical four postures", () => {
    expect(POSTURE_ARCHETYPES).toContain(IDLE_EXPRESSIVE.posture);
  });
});

// ─── Operator ID ─────────────────────────────────────────────────────

describe("Operator ID", () => {
  test("DEFAULT_AGENT_CONFIG uses canonical operator ID", () => {
    expect(DEFAULT_AGENT_CONFIG.operatorId).toBe(CANONICAL_OPERATOR_ID);
  });

  test("createFreshMirror uses canonical operator ID", () => {
    const mirror = createFreshMirror("test-node");
    expect(mirror.profile.operatorId).toBe(CANONICAL_OPERATOR_ID);
  });

  test("operator context starts with full sovereignty", () => {
    expect(OPERATOR_CONTEXT_IDLE.sovereignty).toBe(1);
    expect(OPERATOR_CONTEXT_IDLE.governorOverridden).toBe(false);
  });
});

// ─── Lifecycle Baseline ──────────────────────────────────────────────

describe("Lifecycle Baseline", () => {
  test("IDLE_LIFECYCLE starts at discovered phase with zero counts", () => {
    expect(IDLE_LIFECYCLE.phase).toBe("discovered");
    expect(IDLE_LIFECYCLE.heartbeatCount).toBe(0);
    expect(IDLE_LIFECYCLE.errorCount).toBe(0);
    expect(IDLE_LIFECYCLE.joinedAt).toBeNull();
  });

  test("fresh mirror has correct risk tier (medium — unknown node)", () => {
    const mirror = createFreshMirror("test");
    expect(mirror.risk).toBe("medium");
    expect(mirror.status).toBe("unknown");
  });
});

// ─── Posture Bridge ──────────────────────────────────────────────────

describe("Posture Bridge (NodePosture ↔ DaedalusPosture)", () => {
  test("CALM → companion", () => {
    expect(nodePostureToDaedalusPosture("CALM")).toBe("companion");
  });

  test("ALERT → sentinel", () => {
    expect(nodePostureToDaedalusPosture("ALERT")).toBe("sentinel");
  });

  test("DEFENSIVE → sentinel", () => {
    expect(nodePostureToDaedalusPosture("DEFENSIVE")).toBe("sentinel");
  });

  test("DEGRADED → dormant", () => {
    expect(nodePostureToDaedalusPosture("DEGRADED")).toBe("dormant");
  });

  test("round-trip: all DaedalusPosture values produce valid NodePosture", () => {
    for (const dp of POSTURE_ARCHETYPES) {
      const np = daedalusPostureToNodePosture(dp);
      expect(["CALM", "ALERT", "DEFENSIVE", "DEGRADED"]).toContain(np);
    }
  });
});
