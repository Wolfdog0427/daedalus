import crypto from "crypto";
import type {
  GovernanceOverride,
  ContinuityDrift,
  PostureState,
  PostureSnapshot,
  BeingIdFull,
  BeingVote,
} from "../../../shared/daedalus/contracts";
import { getDaedalusEventBus, nowIso } from "../DaedalusEventBus";

export class GovernanceService {
  private overrides: GovernanceOverride[] = [];
  private drifts: ContinuityDrift[] = [];
  private votes: BeingVote[] = [];
  private posture: PostureSnapshot = {
    posture: "OPEN",
    reason: "Initial state",
    since: nowIso(),
    activeOverrides: [],
    activeDrifts: [],
  };

  sweepExpired(): { expiredOverrides: number; expiredDrifts: number } {
    const now = new Date().getTime();
    const origOverrides = this.overrides.length;
    const origDrifts = this.drifts.length;

    this.overrides = this.overrides.filter(
      (o) => !o.expiresAt || new Date(o.expiresAt).getTime() > now,
    );
    this.drifts = this.drifts.filter(
      (d) => !d.expiresAt || new Date(d.expiresAt).getTime() > now,
    );

    const expiredOverrides = origOverrides - this.overrides.length;
    const expiredDrifts = origDrifts - this.drifts.length;

    if (expiredOverrides > 0 || expiredDrifts > 0) {
      this.recomputePosture();
    }

    return { expiredOverrides, expiredDrifts };
  }

  getPostureSnapshot(): PostureSnapshot {
    return this.posture;
  }

  listOverrides(): GovernanceOverride[] {
    return this.overrides;
  }

  listDrifts(): ContinuityDrift[] {
    return this.drifts;
  }

  castVote(vote: BeingVote): BeingVote {
    this.votes = this.votes.filter(
      (v) => v.being.id !== vote.being.id,
    );
    if (this.votes.length >= 50) {
      return vote; // cap reached
    }
    this.votes.push(vote);

    getDaedalusEventBus().publish({
      type: "BEING_VOTE_CAST",
      timestamp: nowIso(),
      summary: `Being "${vote.being.label}" voted ${vote.vote} (weight ${vote.weight})`,
      beings: [vote],
    });

    this.recomputePosture();
    return vote;
  }

  listVotes(): BeingVote[] {
    return this.votes;
  }

  clearVotes(): void {
    this.votes = [];
    this.recomputePosture();
  }

  removeOverride(overrideId: string): boolean {
    const idx = this.overrides.findIndex((o) => o.id === overrideId);
    if (idx === -1) return false;
    this.overrides.splice(idx, 1);
    this.recomputePosture();
    return true;
  }

  clearOverrides(): void {
    this.overrides = [];
    this.recomputePosture();
  }

  clearDrifts(): void {
    this.drifts = [];
    this.recomputePosture();
  }

  private static readonly MAX_OVERRIDES = 200;
  private static readonly MAX_DRIFTS = 200;

  applyOverride(input: {
    createdBy: BeingIdFull;
    reason: string;
    scope: GovernanceOverride["scope"];
    targetId?: string;
    effect: GovernanceOverride["effect"];
    expiresAt?: string;
  }): GovernanceOverride {
    const override: GovernanceOverride = {
      ...input,
      id: crypto.randomUUID(),
      createdAt: nowIso(),
    };
    if (input.expiresAt) override.expiresAt = input.expiresAt;
    if (this.overrides.length >= GovernanceService.MAX_OVERRIDES) {
      this.overrides.shift();
    }
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
    expiresAt?: string;
  }): ContinuityDrift {
    const drift: ContinuityDrift = {
      ...input,
      id: crypto.randomUUID(),
      detectedAt: nowIso(),
    };
    if (input.expiresAt) drift.expiresAt = input.expiresAt;
    if (this.drifts.length >= GovernanceService.MAX_DRIFTS) {
      this.drifts.shift();
    }
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

    const totalVoteWeight = this.votes.reduce((sum, v) => sum + v.weight, 0);
    const denyWeight = this.votes
      .filter((v) => v.vote === "DENY")
      .reduce((sum, v) => sum + v.weight, 0);
    const escalateWeight = this.votes
      .filter((v) => v.vote === "ESCALATE")
      .reduce((sum, v) => sum + v.weight, 0);
    const hasWeightedDeny = totalVoteWeight > 0 && denyWeight / totalVoteWeight > 0.5;
    const hasWeightedEscalate = totalVoteWeight > 0 && escalateWeight / totalVoteWeight > 0.5;

    if (hasGlobalDeny || hasWeightedDeny) {
      posture = "LOCKDOWN";
      reason = hasGlobalDeny
        ? "Global deny override active"
        : "Majority being vote: DENY";
    } else if (hasSevereDrift || hasWeightedEscalate) {
      posture = "GUARDED";
      reason = hasSevereDrift
        ? "High-severity continuity drift detected"
        : "Majority being vote: ESCALATE";
    } else if (hasMediumDrift || this.overrides.length > 0 || this.votes.length > 0) {
      posture = "ATTENTIVE";
      reason = this.votes.length > 0
        ? "Active being votes present"
        : "Active overrides or medium-severity drifts";
    }

    const changed = posture !== this.posture.posture;

    this.posture = {
      posture,
      reason,
      since: changed ? nowIso() : this.posture.since,
      activeOverrides: [...this.overrides],
      activeDrifts: [...this.drifts],
    };

    if (changed) {
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
