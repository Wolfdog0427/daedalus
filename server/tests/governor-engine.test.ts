import { governOutput, computeGovernorDisplay } from "../../shared/daedalus/governorEngine";
import { makeInitialGovernorState, GOVERNOR_COOLDOWN_MS, ESCALATION_LOCK_MS, GOVERNOR_PRESETS } from "../../shared/daedalus/governor";
import type { GovernorState, GovernorConfig } from "../../shared/daedalus/governor";
import type { ConductorOutput } from "../../shared/daedalus/conductor";
import { CONDUCTOR_DEFAULTS } from "../../shared/daedalus/conductor";

function makeOutput(overrides: Partial<ConductorOutput> = {}): ConductorOutput {
  return { ...CONDUCTOR_DEFAULTS, updatedAt: Date.now(), ...overrides };
}

function makeState(overrides: Partial<GovernorState> = {}): GovernorState {
  return {
    ...makeInitialGovernorState(CONDUCTOR_DEFAULTS),
    ...overrides,
  };
}

describe("governOutput", () => {
  // ── Passthrough ──

  it("passes through when mode and tone are unchanged", () => {
    const raw = makeOutput({ mode: "resting", tone: "neutral" });
    const prev = makeState({ mode: "resting", tone: "neutral" });
    const { governed } = governOutput(raw, prev, 100000);
    expect(governed.mode).toBe("resting");
    expect(governed.tone).toBe("neutral");
  });

  it("passes through continuous values (glow, motion) unchanged", () => {
    const raw = makeOutput({ glowIntensity: 0.77, motionIntensity: 0.33 });
    const prev = makeState();
    const { governed } = governOutput(raw, prev, 100000);
    expect(governed.glowIntensity).toBe(0.77);
    expect(governed.motionIntensity).toBe(0.33);
  });

  // ── Mode hysteresis ──

  it("blocks mode change during cooldown", () => {
    const now = 5000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: now - 200 });
    const raw = makeOutput({ mode: "attentive" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.mode).toBe("resting");
  });

  it("allows mode change after cooldown expires", () => {
    const now = 5000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: now - GOVERNOR_COOLDOWN_MS - 1 });
    const raw = makeOutput({ mode: "attentive" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.mode).toBe("attentive");
  });

  // ── Tone hysteresis ──

  it("blocks tone change during cooldown", () => {
    const now = 5000;
    const prev = makeState({ tone: "neutral", lastToneChangeAt: now - 200 });
    const raw = makeOutput({ tone: "focused" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.tone).toBe("neutral");
  });

  it("allows tone change after cooldown expires", () => {
    const now = 5000;
    const prev = makeState({ tone: "neutral", lastToneChangeAt: now - GOVERNOR_COOLDOWN_MS - 1 });
    const raw = makeOutput({ tone: "focused" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.tone).toBe("focused");
  });

  // ── Escalation lock ──

  it("holds escalated mode for ESCALATION_LOCK_MS after entering", () => {
    const enterTime = 10000;
    const raw1 = makeOutput({ mode: "escalated", tone: "alert" });
    const prev = makeState({ lastModeChangeAt: 0, lastToneChangeAt: 0 });

    const { governed: g1, nextState: s1 } = governOutput(raw1, prev, enterTime);
    expect(g1.mode).toBe("escalated");
    expect(g1.tone).toBe("alert");
    expect(s1.escalationLockedUntil).toBe(enterTime + ESCALATION_LOCK_MS);

    // Still locked 1s later even if conductor says "resting"
    const raw2 = makeOutput({ mode: "resting", tone: "neutral" });
    const { governed: g2 } = governOutput(raw2, s1, enterTime + 1000);
    expect(g2.mode).toBe("escalated");
    expect(g2.tone).toBe("alert");

    // Unlocked after lock expires
    const { governed: g3 } = governOutput(raw2, s1, enterTime + ESCALATION_LOCK_MS + 1);
    expect(g3.mode).toBe("resting");
  });

  it("extends escalation lock when conductor keeps saying escalated", () => {
    const t0 = 10000;
    const raw = makeOutput({ mode: "escalated", tone: "alert" });
    const prev = makeState();

    const { nextState: s1 } = governOutput(raw, prev, t0);
    expect(s1.escalationLockedUntil).toBe(t0 + ESCALATION_LOCK_MS);

    const { nextState: s2 } = governOutput(raw, s1, t0 + 2000);
    expect(s2.escalationLockedUntil).toBe(t0 + 2000 + ESCALATION_LOCK_MS);
  });

  it("suppresses continuity badge during escalation lock", () => {
    const now = 10000;
    const raw = makeOutput({
      mode: "escalated",
      tone: "alert",
      continuityBadge: { kind: "threshold", label: "10 check-ins" },
    });
    const prev = makeState();
    const { governed } = governOutput(raw, prev, now);
    expect(governed.continuityBadge).toBeNull();
  });

  it("allows continuity badge when not in escalation lock", () => {
    const now = 100000;
    const raw = makeOutput({
      mode: "celebrating",
      tone: "celebratory",
      continuityBadge: { kind: "threshold", label: "10 check-ins" },
    });
    const prev = makeState({ mode: "celebrating", lastModeChangeAt: 0 });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.continuityBadge).toEqual({ kind: "threshold", label: "10 check-ins" });
  });

  // ── Posture follows mode ──

  it("holds posture when mode is held back by cooldown", () => {
    const now = 5000;
    const prev = makeState({
      mode: "resting",
      posture: "companion",
      lastModeChangeAt: now - 200,
    });
    const raw = makeOutput({ mode: "attentive", posture: "sentinel" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.posture).toBe("companion");
  });

  it("allows posture change when mode change is allowed", () => {
    const now = 5000;
    const prev = makeState({
      mode: "resting",
      posture: "companion",
      lastModeChangeAt: now - GOVERNOR_COOLDOWN_MS - 1,
    });
    const raw = makeOutput({ mode: "attentive", posture: "sentinel" });
    const { governed } = governOutput(raw, prev, now);
    expect(governed.posture).toBe("sentinel");
  });

  // ── Suppress ambient pulse ──

  it("forces suppressAmbientPulse during escalation", () => {
    const raw = makeOutput({ mode: "escalated", suppressAmbientPulse: false });
    const prev = makeState();
    const { governed } = governOutput(raw, prev, 10000);
    expect(governed.suppressAmbientPulse).toBe(true);
  });

  // ── State tracking ──

  it("updates lastModeChangeAt when mode actually changes", () => {
    const now = 50000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: 0 });
    const raw = makeOutput({ mode: "attentive" });
    const { nextState } = governOutput(raw, prev, now);
    expect(nextState.lastModeChangeAt).toBe(now);
  });

  it("does not update lastModeChangeAt when mode is held", () => {
    const now = 5000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: now - 200 });
    const raw = makeOutput({ mode: "attentive" });
    const { nextState } = governOutput(raw, prev, now);
    expect(nextState.lastModeChangeAt).toBe(now - 200);
  });

  // ── Config: disabled ──

  it("passes through raw output when config.enabled is false", () => {
    const raw = makeOutput({ mode: "celebrating", tone: "celebratory" });
    const prev = makeState({ mode: "resting", tone: "neutral", lastModeChangeAt: Date.now() });
    const config: GovernorConfig = { enabled: false, cooldownMs: 900, escalationLockMs: 2500 };
    const { governed } = governOutput(raw, prev, Date.now(), config);
    expect(governed.mode).toBe("celebrating");
    expect(governed.tone).toBe("celebratory");
  });

  // ── Config: presets ──

  it("responsive preset allows faster mode changes", () => {
    const config = GOVERNOR_PRESETS.responsive;
    const now = 5000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: now - 500 });
    const raw = makeOutput({ mode: "attentive" });

    const defaultResult = governOutput(raw, prev, now, GOVERNOR_PRESETS.default);
    expect(defaultResult.governed.mode).toBe("resting");

    const responsiveResult = governOutput(raw, prev, now, config);
    expect(responsiveResult.governed.mode).toBe("attentive");
  });

  it("calm preset enforces longer cooldown", () => {
    const config = GOVERNOR_PRESETS.calm;
    const now = 5000;
    const prev = makeState({ mode: "resting", lastModeChangeAt: now - 1200 });
    const raw = makeOutput({ mode: "attentive" });

    const defaultResult = governOutput(raw, prev, now, GOVERNOR_PRESETS.default);
    expect(defaultResult.governed.mode).toBe("attentive");

    const calmResult = governOutput(raw, prev, now, config);
    expect(calmResult.governed.mode).toBe("resting");
  });

  it("calm preset extends escalation lock duration", () => {
    const config = GOVERNOR_PRESETS.calm;
    const enterTime = 10000;
    const raw1 = makeOutput({ mode: "escalated", tone: "alert" });
    const prev = makeState();

    const { nextState: s1 } = governOutput(raw1, prev, enterTime, config);
    expect(s1.escalationLockedUntil).toBe(enterTime + config.escalationLockMs);

    const raw2 = makeOutput({ mode: "resting", tone: "neutral" });
    const { governed } = governOutput(raw2, s1, enterTime + 3000, config);
    expect(governed.mode).toBe("escalated");
  });
});

describe("computeGovernorDisplay", () => {
  it("reports enabled when config is enabled", () => {
    const state = makeState();
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, 100000);
    expect(display.enabled).toBe(true);
  });

  it("reports disabled when config is disabled", () => {
    const state = makeState();
    const config: GovernorConfig = { enabled: false, cooldownMs: 900, escalationLockMs: 2500 };
    const display = computeGovernorDisplay(state, config, 100000);
    expect(display.enabled).toBe(false);
  });

  it("reports escalation lock when within lock window", () => {
    const now = 10000;
    const state = makeState({ escalationLockedUntil: now + 1000 });
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(display.escalationLocked).toBe(true);
  });

  it("reports no escalation lock after window expires", () => {
    const now = 10000;
    const state = makeState({ escalationLockedUntil: now - 1 });
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(display.escalationLocked).toBe(false);
  });

  it("reports mode cooldown active when within window", () => {
    const now = 5000;
    const state = makeState({ lastModeChangeAt: now - 200 });
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(display.modeCooldownActive).toBe(true);
  });

  it("reports mode cooldown inactive after window", () => {
    const now = 5000;
    const state = makeState({ lastModeChangeAt: now - GOVERNOR_COOLDOWN_MS - 1 });
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(display.modeCooldownActive).toBe(false);
  });

  it("reports tone cooldown active when within window", () => {
    const now = 5000;
    const state = makeState({ lastToneChangeAt: now - 200 });
    const display = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(display.toneCooldownActive).toBe(true);
  });

  it("uses preset-specific cooldown for display", () => {
    const now = 5000;
    const state = makeState({ lastModeChangeAt: now - 500 });

    const defaultDisplay = computeGovernorDisplay(state, GOVERNOR_PRESETS.default, now);
    expect(defaultDisplay.modeCooldownActive).toBe(true);

    const responsiveDisplay = computeGovernorDisplay(state, GOVERNOR_PRESETS.responsive, now);
    expect(responsiveDisplay.modeCooldownActive).toBe(false);
  });
});
