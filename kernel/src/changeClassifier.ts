/**
 * Impact Classifier + Invariant Touch Detector
 *
 * Surface-based change classification. Every proposed change declares
 * which surfaces it touches and how deep it goes. The classifier
 * computes a composite score → low / medium / high impact.
 *
 * The invariant detector maps surfaces to constitutional invariants.
 * Any change touching an invariant surface is blocked from auto-approval.
 */

import type {
  ChangeSurface,
  ChangeDepth,
  ChangeImpact,
  ChangeImpactInput,
  ChangeImpactResult,
  InvariantSurface,
  InvariantTouchResult,
} from "./types";

// ── Surface Risk Tiers ──────────────────────────────────────────────

const HIGH_RISK_SURFACES: ReadonlySet<ChangeSurface> = new Set([
  "governance_policy",
  "identity",
  "continuity",
  "posture",
  "node_authority",
  "persistence",
  "network_topology",
  "alignment_tuning",
]);

const MEDIUM_RISK_SURFACES: ReadonlySet<ChangeSurface> = new Set([
  "performance_tuning",
  "non_critical_config",
]);

const LOW_RISK_SURFACES: ReadonlySet<ChangeSurface> = new Set([
  "telemetry",
  "logging",
  "ui_presentation",
]);

// ── Impact Classification ───────────────────────────────────────────

export function classifyChangeImpact(input: ChangeImpactInput): ChangeImpactResult {
  const { surfaces, depth, reversible } = input;
  const reasons: string[] = [];
  let score = 0;

  if (surfaces.some(s => HIGH_RISK_SURFACES.has(s))) {
    score += 3;
    reasons.push("touches_high_risk_surface");
  }

  if (surfaces.some(s => MEDIUM_RISK_SURFACES.has(s))) {
    score += 2;
    reasons.push("touches_medium_risk_surface");
  }

  if (surfaces.some(s => LOW_RISK_SURFACES.has(s))) {
    score += 1;
    reasons.push("touches_low_risk_surface");
  }

  if (surfaces.length === 0) {
    score += 1;
    reasons.push("no_surfaces_declared");
  }

  switch (depth) {
    case "deep":
      score += 3;
      reasons.push("deep_change");
      break;
    case "moderate":
      score += 2;
      reasons.push("moderate_change");
      break;
    case "shallow":
      score += 1;
      reasons.push("shallow_change");
      break;
  }

  if (!reversible) {
    score += 3;
    reasons.push("irreversible_change");
  } else {
    reasons.push("reversible_change");
  }

  let impact: ChangeImpact;
  if (score <= 3) {
    impact = "low";
  } else if (score <= 6) {
    impact = "medium";
  } else {
    impact = "high";
  }

  return { impact, score, reasons };
}

// ── Invariant Touch Detection ───────────────────────────────────────

const SURFACE_TO_INVARIANT: Readonly<Record<ChangeSurface, InvariantSurface | null>> = {
  telemetry: null,
  logging: null,
  ui_presentation: null,
  non_critical_config: null,
  performance_tuning: null,
  alignment_tuning: "alignment_core",
  governance_policy: "governance_policy",
  identity: "identity",
  continuity: "continuity",
  posture: "posture",
  node_authority: "node_authority",
  persistence: "continuity",
  network_topology: "node_authority",
};

export function detectInvariantTouchBySurface(surfaces: ChangeSurface[]): InvariantTouchResult {
  const invariantsTouched: InvariantSurface[] = [];

  for (const s of surfaces) {
    const mapped = SURFACE_TO_INVARIANT[s];
    if (mapped && !invariantsTouched.includes(mapped)) {
      invariantsTouched.push(mapped);
    }
  }

  return {
    touchesInvariants: invariantsTouched.length > 0,
    invariantsTouched,
  };
}

// ── Combined Classification ─────────────────────────────────────────

export interface FullClassificationResult {
  impact: ChangeImpactResult;
  invariants: InvariantTouchResult;
}

/**
 * Runs both the impact classifier and invariant detector together.
 * Convenience for the approval gate pipeline.
 */
export function classifyChange(input: ChangeImpactInput): FullClassificationResult {
  const impact = classifyChangeImpact(input);
  const invariants = detectInvariantTouchBySurface(input.surfaces);
  return { impact, invariants };
}

export { HIGH_RISK_SURFACES, MEDIUM_RISK_SURFACES, LOW_RISK_SURFACES, SURFACE_TO_INVARIANT };
