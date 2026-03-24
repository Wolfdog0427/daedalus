import crypto from "crypto";
import type {
  GovernanceOverride,
  ContinuityDrift,
  PostureState,
  PostureSnapshot,
  BeingIdFull,
} from "../../../shared/daedalus/contracts";
import { getDaedalusEventBus, nowIso } from "../DaedalusEventBus";

export class GovernanceService {
  private overrides: GovernanceOverride[] = [];
  private drifts: ContinuityDrift[] = [];
  private posture: PostureSnapshot = {
    posture: "OPEN",
    reason: "Initial state",
    since: nowIso(),
    activeOverrides: [],
    activeDrifts: [],
  };

  getPostureSnapshot(): PostureSnapshot {
    return this.posture;
  }

  listOverrides(): GovernanceOverride[] {
    return this.overrides;
  }

  listDrifts(): ContinuityDrift[] {
    return this.drifts;
  }

  applyOverride(input: {
    createdBy: BeingIdFull;
    reason: string;
    scope: GovernanceOverride["scope"];
    targetId?: string;
    effect: GovernanceOverride["effect"];
  }): GovernanceOverride {
    const override: GovernanceOverride = {
      ...input,
      id: crypto.randomUUID(),
      createdAt: nowIso(),
    };
    this.overrides.push(override);

    getDaedalusEventBus().publish({
      type: "GOVERNANCE_OVERRIDE_APPLIED",
      timestamp: nowIso(),
      governanceOverrideId: override.id,
      summary: override.reason,
    });

    this.recomputePosture();
    return override;
  }

  recordDrift(input: {
    severity: ContinuityDrift["severity"];
    summary: string;
  }): ContinuityDrift {
    const drift: ContinuityDrift = {
      ...input,
      id: crypto.randomUUID(),
      detectedAt: nowIso(),
    };
    this.drifts.push(drift);

    getDaedalusEventBus().publish({
      type: "CONTINUITY_DRIFT_DETECTED",
      timestamp: nowIso(),
      continuityDriftId: drift.id,
      summary: drift.summary,
    });

    this.recomputePosture();
    return drift;
  }

  private recomputePosture(): void {
    let posture: PostureState = "OPEN";
    let reason = "Normal conditions";

    const hasGlobalDeny = this.overrides.some(
      (o) => o.scope === "GLOBAL" && o.effect === "DENY",
    );
    const hasSevereDrift = this.drifts.some((d) => d.severity === "HIGH");
    const hasMediumDrift = this.drifts.some((d) => d.severity === "MEDIUM");

    if (hasGlobalDeny) {
      posture = "LOCKDOWN";
      reason = "Global deny override active";
    } else if (hasSevereDrift) {
      posture = "GUARDED";
      reason = "High-severity continuity drift detected";
    } else if (hasMediumDrift || this.overrides.length > 0) {
      posture = "ATTENTIVE";
      reason = "Active overrides or medium-severity drifts";
    }

    if (posture !== this.posture.posture) {
      this.posture = {
        posture,
        reason,
        since: nowIso(),
        activeOverrides: this.overrides,
        activeDrifts: this.drifts,
      };

      getDaedalusEventBus().publish({
        type: "POSTURE_CHANGED",
        timestamp: nowIso(),
        posture,
        summary: reason,
      });
    }
  }
}

export const governanceService = new GovernanceService();
