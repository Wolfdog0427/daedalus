import {
  detectIssue,
  recommendForIssue,
  evolveGovernance,
  evaluateGovernance,
} from "../../shared/daedalus/metaGovernanceEngine";
import type { AnalyticsSnapshot } from "../../shared/daedalus/sceneAnalytics";
import { ANALYTICS_IDLE } from "../../shared/daedalus/sceneAnalytics";
import {
  META_GOVERNANCE_DEFAULTS,
  META_GOVERNANCE_EVAL_IDLE,
} from "../../shared/daedalus/metaGovernance";
import type { MetaGovernanceEvalState } from "../../shared/daedalus/metaGovernance";
import type { ExpressiveStrategy } from "../../shared/daedalus/expressiveStrategy";
import type { MetaStrategy } from "../../shared/daedalus/metaStrategy";

const NOW = 300_000;

function mkAnalytics(overrides: Partial<AnalyticsSnapshot> = {}): AnalyticsSnapshot {
  return { ...ANALYTICS_IDLE, timestamp: NOW, expressiveHealth: 0.7, ...overrides };
}

// ── detectIssue ────────────────────────────────────────────────

describe("detectIssue", () => {
  it("returns timeline-instability when volatility > 0.7", () => {
    expect(detectIssue(mkAnalytics({ momentumVolatility: 0.8 }), null, null)).toBe(
      "timeline-instability",
    );
  });

  it("returns grammar-instability when rejection rate > 2", () => {
    expect(detectIssue(mkAnalytics({ grammarRejectionRate: 3 }), null, null)).toBe(
      "grammar-instability",
    );
  });

  it("returns narrative-overdensity when density > 5", () => {
    expect(detectIssue(mkAnalytics({ narrativeDensity: 6 }), null, null)).toBe(
      "narrative-overdensity",
    );
  });

  it("returns overcorrection when health < 0.3", () => {
    expect(detectIssue(mkAnalytics({ expressiveHealth: 0.2 }), null, null)).toBe(
      "overcorrection",
    );
  });

  it("returns governor-imbalance when intervention rate > 3", () => {
    expect(detectIssue(mkAnalytics({ governorInterventionRate: 4 }), null, null)).toBe(
      "governor-imbalance",
    );
  });

  it("returns undercorrection when health > 0.92", () => {
    expect(detectIssue(mkAnalytics({ expressiveHealth: 0.95 }), null, null)).toBe(
      "undercorrection",
    );
  });

  it("returns strategy-conflict for sustained-focus vs exploration-cycle", () => {
    expect(
      detectIssue(mkAnalytics(), "sustained-focus", "exploration-cycle"),
    ).toBe("strategy-conflict");
  });

  it("returns strategy-conflict for broad-exploration vs stability-cycle", () => {
    expect(
      detectIssue(mkAnalytics(), "broad-exploration", "stability-cycle"),
    ).toBe("strategy-conflict");
  });

  it("returns strategy-conflict for cooldown-arc vs responsiveness-cycle", () => {
    expect(
      detectIssue(mkAnalytics(), "cooldown-arc", "responsiveness-cycle"),
    ).toBe("strategy-conflict");
  });

  it("returns strategy-conflict for responsiveness-first vs cooldown-cycle", () => {
    expect(
      detectIssue(mkAnalytics(), "responsiveness-first", "cooldown-cycle"),
    ).toBe("strategy-conflict");
  });

  it("returns null when no issues detected", () => {
    expect(detectIssue(mkAnalytics(), null, null)).toBeNull();
  });

  it("returns null for aligned strategy and meta-strategy", () => {
    expect(
      detectIssue(mkAnalytics(), "sustained-focus", "stability-cycle"),
    ).toBeNull();
  });

  it("timeline-instability takes priority over overcorrection", () => {
    expect(
      detectIssue(
        mkAnalytics({ momentumVolatility: 0.8, expressiveHealth: 0.2 }),
        null,
        null,
      ),
    ).toBe("timeline-instability");
  });
});

// ── recommendForIssue ──────────────────────────────────────────

describe("recommendForIssue", () => {
  it("timeline-instability increases smoothing + blend", () => {
    const rec = recommendForIssue("timeline-instability");
    expect(rec.timelineMomentumHalfLifeMs).toBe(13000);
    expect(rec.grammarDefaultBlendMs).toBe(750);
  });

  it("grammar-instability increases dwell + blend", () => {
    const rec = recommendForIssue("grammar-instability");
    expect(rec.grammarDefaultDwellMs).toBe(1600);
    expect(rec.grammarDefaultBlendMs).toBe(800);
  });

  it("narrative-overdensity increases interval", () => {
    const rec = recommendForIssue("narrative-overdensity");
    expect(rec.narrativeMinIntervalMs).toBe(7000);
  });

  it("overcorrection relaxes governor + blend", () => {
    const rec = recommendForIssue("overcorrection");
    expect(rec.governorCooldownMs).toBe(800);
    expect(rec.grammarDefaultBlendMs).toBe(450);
  });

  it("undercorrection tightens governor + blend", () => {
    const rec = recommendForIssue("undercorrection");
    expect(rec.governorCooldownMs).toBe(550);
    expect(rec.grammarDefaultBlendMs).toBe(300);
  });

  it("strategy-conflict recommends moderate tuning", () => {
    const rec = recommendForIssue("strategy-conflict");
    expect(rec.grammarDefaultBlendMs).toBe(600);
    expect(rec.timelineMomentumHalfLifeMs).toBe(8000);
  });

  it("governor-imbalance widens cooldowns", () => {
    const rec = recommendForIssue("governor-imbalance");
    expect(rec.governorCooldownMs).toBe(1200);
    expect(rec.governorEscalationLockMs).toBe(3800);
  });
});

// ── evolveGovernance ───────────────────────────────────────────

describe("evolveGovernance", () => {
  it("starts from idle with reinforceStep on first detection", () => {
    const next = evolveGovernance(
      META_GOVERNANCE_EVAL_IDLE,
      mkAnalytics({ momentumVolatility: 0.8 }),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("timeline-instability");
    expect(next.confidence).toBe(META_GOVERNANCE_DEFAULTS.reinforceStep);
  });

  it("reinforces confidence when candidate matches", () => {
    const prev: MetaGovernanceEvalState = {
      candidate: "timeline-instability",
      confidence: 0.4,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveGovernance(
      prev,
      mkAnalytics({ momentumVolatility: 0.8 }),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(0.4 + META_GOVERNANCE_DEFAULTS.reinforceStep);
  });

  it("caps confidence at 1", () => {
    const prev: MetaGovernanceEvalState = {
      candidate: "overcorrection",
      confidence: 0.95,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveGovernance(
      prev,
      mkAnalytics({ expressiveHealth: 0.2 }),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(1);
  });

  it("resets to new candidate when detection changes", () => {
    const prev: MetaGovernanceEvalState = {
      candidate: "timeline-instability",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveGovernance(
      prev,
      mkAnalytics({ grammarRejectionRate: 3 }),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("grammar-instability");
    expect(next.confidence).toBe(META_GOVERNANCE_DEFAULTS.reinforceStep);
  });

  it("weakens confidence when no issue detected", () => {
    const prev: MetaGovernanceEvalState = {
      candidate: "overcorrection",
      confidence: 0.5,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveGovernance(
      prev,
      mkAnalytics(),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(0.5 - META_GOVERNANCE_DEFAULTS.weakenStep);
  });

  it("applies time-based decay", () => {
    const prev: MetaGovernanceEvalState = {
      candidate: "overcorrection",
      confidence: 0.8,
      lastEvalAt: NOW - 35000,
    };
    const next = evolveGovernance(
      prev,
      mkAnalytics({ expressiveHealth: 0.2 }),
      null,
      null,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(
      0.8 - META_GOVERNANCE_DEFAULTS.decayStep + META_GOVERNANCE_DEFAULTS.reinforceStep,
    );
  });

  it("detects strategy-conflict from cross-tier inputs", () => {
    const next = evolveGovernance(
      META_GOVERNANCE_EVAL_IDLE,
      mkAnalytics(),
      "sustained-focus",
      "exploration-cycle",
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("strategy-conflict");
  });
});

// ── evaluateGovernance ─────────────────────────────────────────

describe("evaluateGovernance", () => {
  it("returns no proposal when confidence is below threshold", () => {
    const result = evaluateGovernance(
      META_GOVERNANCE_EVAL_IDLE,
      mkAnalytics({ momentumVolatility: 0.8 }),
      null,
      null,
      0,
      1,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
    expect(result.state.candidate).toBe("timeline-instability");
  });

  it("returns no proposal when within proposalIntervalMs", () => {
    const state: MetaGovernanceEvalState = {
      candidate: "overcorrection",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateGovernance(
      state,
      mkAnalytics({ expressiveHealth: 0.2 }),
      null,
      null,
      NOW - 5000,
      1,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
  });

  it("produces a proposal when confidence exceeds threshold and interval elapsed", () => {
    const state: MetaGovernanceEvalState = {
      candidate: "overcorrection",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateGovernance(
      state,
      mkAnalytics({ expressiveHealth: 0.2 }),
      null,
      null,
      0,
      99,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.proposal).not.toBeNull();
    expect(result.proposal!.id).toBe(99);
    expect(result.proposal!.reason).toContain("overcorrection");
    expect(result.proposal!.recommended.governorCooldownMs).toBe(800);
  });

  it("returns no proposal when candidate is null", () => {
    const result = evaluateGovernance(
      META_GOVERNANCE_EVAL_IDLE,
      mkAnalytics(),
      null,
      null,
      0,
      1,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
  });

  it("includes confidence in proposal reason", () => {
    const state: MetaGovernanceEvalState = {
      candidate: "governor-imbalance",
      confidence: 0.75,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateGovernance(
      state,
      mkAnalytics({ governorInterventionRate: 4 }),
      null,
      null,
      0,
      1,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.proposal!.reason).toMatch(/\d+%/);
  });

  it("updates state even when no proposal is produced", () => {
    const result = evaluateGovernance(
      META_GOVERNANCE_EVAL_IDLE,
      mkAnalytics({ narrativeDensity: 6 }),
      null,
      null,
      0,
      1,
      META_GOVERNANCE_DEFAULTS,
      NOW,
    );
    expect(result.state.candidate).toBe("narrative-overdensity");
    expect(result.state.lastEvalAt).toBe(NOW);
    expect(result.proposal).toBeNull();
  });
});
