import {
  identifyActiveTiers,
  capTuning,
  consolidate,
} from "../../shared/daedalus/postAutonomyEngine";
import type { AdaptationTuning } from "../../shared/daedalus/sceneAdaptation";
import type { TierName, PostAutonomyConfig } from "../../shared/daedalus/postAutonomy";
import { POST_AUTONOMY_DEFAULTS } from "../../shared/daedalus/postAutonomy";

// ── identifyActiveTiers ────────────────────────────────────────

describe("identifyActiveTiers", () => {
  it("returns empty array when all tiers are empty", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: {},
      "tier-0": {},
      "tier-1": {},
      "tier-3": {},
      "tier-4": {},
      "tier-5": {},
    };
    expect(identifyActiveTiers(tiers)).toEqual([]);
  });

  it("identifies single active tier", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": {},
      "tier-1": {},
    };
    expect(identifyActiveTiers(tiers)).toEqual(["adaptation"]);
  });

  it("identifies multiple active tiers", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": { grammarDefaultBlendMs: 700 },
      "tier-1": {},
      "tier-3": { timelineMomentumHalfLifeMs: 5000 },
    };
    expect(identifyActiveTiers(tiers)).toEqual(["adaptation", "tier-0", "tier-3"]);
  });

  it("identifies all six tiers when active", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": { grammarDefaultBlendMs: 700 },
      "tier-1": { narrativeMinIntervalMs: 3000 },
      "tier-3": { timelineMomentumHalfLifeMs: 5000 },
      "tier-4": { grammarDefaultDwellMs: 1200 },
      "tier-5": { governorEscalationLockMs: 3500 },
    };
    expect(identifyActiveTiers(tiers)).toHaveLength(6);
  });

  it("handles partial tier map", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      "tier-0": { grammarDefaultBlendMs: 400 },
    };
    expect(identifyActiveTiers(tiers)).toEqual(["tier-0"]);
  });
});

// ── capTuning ──────────────────────────────────────────────────

describe("capTuning", () => {
  it("returns unchanged tuning when within bounds", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 800,
      grammarDefaultBlendMs: 500,
    };
    const result = capTuning(tuning);
    expect(result.capped).toEqual(tuning);
    expect(result.applied).toBe(false);
  });

  it("clamps values above the maximum", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 5000,
    };
    const result = capTuning(tuning);
    expect(result.capped.governorCooldownMs).toBe(POST_AUTONOMY_DEFAULTS.caps.governorCooldownMs[1]);
    expect(result.applied).toBe(true);
  });

  it("clamps values below the minimum", () => {
    const tuning: AdaptationTuning = {
      grammarDefaultBlendMs: 50,
    };
    const result = capTuning(tuning);
    expect(result.capped.grammarDefaultBlendMs).toBe(POST_AUTONOMY_DEFAULTS.caps.grammarDefaultBlendMs[0]);
    expect(result.applied).toBe(true);
  });

  it("clamps multiple fields independently", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 100,
      governorEscalationLockMs: 9000,
      timelineMomentumHalfLifeMs: 800,
      narrativeMinIntervalMs: 500,
      grammarDefaultDwellMs: 200,
      grammarDefaultBlendMs: 2000,
    };
    const result = capTuning(tuning);
    expect(result.applied).toBe(true);
    expect(result.capped.governorCooldownMs).toBe(400);
    expect(result.capped.governorEscalationLockMs).toBe(5000);
    expect(result.capped.timelineMomentumHalfLifeMs).toBe(3000);
    expect(result.capped.narrativeMinIntervalMs).toBe(1500);
    expect(result.capped.grammarDefaultDwellMs).toBe(500);
    expect(result.capped.grammarDefaultBlendMs).toBe(1000);
  });

  it("does not add fields that were undefined", () => {
    const tuning: AdaptationTuning = {};
    const result = capTuning(tuning);
    expect(result.capped).toEqual({});
    expect(result.applied).toBe(false);
  });

  it("handles exact boundary values without capping", () => {
    const caps = POST_AUTONOMY_DEFAULTS.caps;
    const tuning: AdaptationTuning = {
      governorCooldownMs: caps.governorCooldownMs[0],
      grammarDefaultBlendMs: caps.grammarDefaultBlendMs[1],
    };
    const result = capTuning(tuning);
    expect(result.capped).toEqual(tuning);
    expect(result.applied).toBe(false);
  });

  it("uses custom caps when provided", () => {
    const customCaps = {
      ...POST_AUTONOMY_DEFAULTS.caps,
      governorCooldownMs: [600, 800] as [number, number],
    };
    const tuning: AdaptationTuning = { governorCooldownMs: 1000 };
    const result = capTuning(tuning, customCaps);
    expect(result.capped.governorCooldownMs).toBe(800);
    expect(result.applied).toBe(true);
  });
});

// ── consolidate ────────────────────────────────────────────────

describe("consolidate", () => {
  it("returns idle snapshot when no tiers are active", () => {
    const result = consolidate(
      {},
      { adaptation: {}, "tier-0": {}, "tier-1": {} },
    );
    expect(result.activeTierCount).toBe(0);
    expect(result.activeTiers).toEqual([]);
    expect(result.escalationDetected).toBe(false);
    expect(result.cappingApplied).toBe(false);
    expect(result.effectiveTuning).toEqual({});
  });

  it("reports active tiers correctly", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": { grammarDefaultBlendMs: 500 },
      "tier-1": {},
    };
    const result = consolidate({ governorCooldownMs: 900, grammarDefaultBlendMs: 500 }, tiers);
    expect(result.activeTierCount).toBe(2);
    expect(result.activeTiers).toEqual(["adaptation", "tier-0"]);
  });

  it("detects escalation when active tiers exceed maxActiveTiers", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": { grammarDefaultBlendMs: 500 },
      "tier-1": { narrativeMinIntervalMs: 3000 },
      "tier-3": { timelineMomentumHalfLifeMs: 5000 },
      "tier-4": { grammarDefaultDwellMs: 1200 },
    };
    const result = consolidate(
      { governorCooldownMs: 900 },
      tiers,
    );
    expect(result.escalationDetected).toBe(true);
    expect(result.activeTierCount).toBe(5);
  });

  it("does not flag escalation at exactly maxActiveTiers", () => {
    const tiers: Partial<Record<TierName, AdaptationTuning>> = {
      adaptation: { governorCooldownMs: 900 },
      "tier-0": { grammarDefaultBlendMs: 500 },
      "tier-1": { narrativeMinIntervalMs: 3000 },
      "tier-3": { timelineMomentumHalfLifeMs: 5000 },
    };
    const result = consolidate({ governorCooldownMs: 900 }, tiers);
    expect(result.escalationDetected).toBe(false);
    expect(result.activeTierCount).toBe(4);
  });

  it("applies capping and reports it", () => {
    const result = consolidate(
      { governorCooldownMs: 50000 },
      { adaptation: { governorCooldownMs: 50000 } },
    );
    expect(result.cappingApplied).toBe(true);
    expect(result.effectiveTuning.governorCooldownMs).toBe(
      POST_AUTONOMY_DEFAULTS.caps.governorCooldownMs[1],
    );
  });

  it("passes through safe values uncapped", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 800 };
    const result = consolidate(tuning, { adaptation: tuning });
    expect(result.cappingApplied).toBe(false);
    expect(result.effectiveTuning).toEqual(tuning);
  });

  it("uses custom config", () => {
    const config: PostAutonomyConfig = {
      maxActiveTiers: 1,
      caps: {
        ...POST_AUTONOMY_DEFAULTS.caps,
        governorCooldownMs: [500, 600],
      },
    };
    const result = consolidate(
      { governorCooldownMs: 700 },
      {
        adaptation: { governorCooldownMs: 700 },
        "tier-0": { grammarDefaultBlendMs: 400 },
      },
      config,
    );
    expect(result.escalationDetected).toBe(true);
    expect(result.cappingApplied).toBe(true);
    expect(result.effectiveTuning.governorCooldownMs).toBe(600);
  });
});
