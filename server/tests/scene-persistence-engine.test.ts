import {
  serializeScene,
  validatePersistedScene,
  rehydrateScene,
} from "../../shared/daedalus/scenePersistenceEngine";
import { PERSISTENCE_DEFAULTS } from "../../shared/daedalus/scenePersistence";
import type { OrchestratedScene } from "../../shared/daedalus/sceneOrchestration";
import type { TimelineSnapshot } from "../../shared/daedalus/timeline";
import type { PersistedScene } from "../../shared/daedalus/scenePersistence";

function mkScene(overrides: Partial<OrchestratedScene> = {}): OrchestratedScene {
  return {
    sceneName: "focus",
    mode: "attentive",
    tone: "focused",
    posture: "sentinel",
    glow: 0.7,
    motion: 0.6,
    suppressAmbientPulse: false,
    continuityBadge: { kind: "threshold", label: "5 sessions" },
    narrativeLine: "Attention is aligned.",
    progress: 1,
    blendMs: 0,
    ...overrides,
  };
}

function mkTimeline(overrides: Partial<TimelineSnapshot> = {}): TimelineSnapshot {
  return {
    phase: "rising",
    momentum: 0.55,
    eventCount: 4,
    ...overrides,
  };
}

describe("serializeScene", () => {
  it("extracts all persistable fields", () => {
    const now = 1000000;
    const result = serializeScene(mkScene(), mkTimeline(), now);

    expect(result.timestamp).toBe(now);
    expect(result.sceneName).toBe("focus");
    expect(result.mode).toBe("attentive");
    expect(result.tone).toBe("focused");
    expect(result.posture).toBe("sentinel");
    expect(result.glow).toBe(0.7);
    expect(result.motion).toBe(0.6);
    expect(result.continuityBadge).toEqual({ kind: "threshold", label: "5 sessions" });
    expect(result.narrativeLine).toBe("Attention is aligned.");
    expect(result.momentum).toBe(0.55);
    expect(result.timelinePhase).toBe("rising");
  });

  it("handles null continuityBadge and narrativeLine", () => {
    const result = serializeScene(
      mkScene({ continuityBadge: null, narrativeLine: null }),
      mkTimeline(),
    );
    expect(result.continuityBadge).toBeNull();
    expect(result.narrativeLine).toBeNull();
  });
});

describe("validatePersistedScene", () => {
  const now = 1000000;

  function mkPersisted(overrides: Partial<PersistedScene> = {}): PersistedScene {
    return {
      timestamp: now - 5000,
      sceneName: "focus",
      mode: "attentive",
      tone: "focused",
      posture: "sentinel",
      glow: 0.7,
      motion: 0.6,
      continuityBadge: null,
      narrativeLine: null,
      momentum: 0.5,
      timelinePhase: "rising",
      ...overrides,
    };
  }

  it("returns valid persisted scene when fresh", () => {
    const result = validatePersistedScene(mkPersisted(), PERSISTENCE_DEFAULTS, now);
    expect(result).not.toBeNull();
    expect(result!.sceneName).toBe("focus");
  });

  it("returns null when timestamp is too old", () => {
    const old = mkPersisted({ timestamp: now - PERSISTENCE_DEFAULTS.maxAgeMs - 1 });
    const result = validatePersistedScene(old, PERSISTENCE_DEFAULTS, now);
    expect(result).toBeNull();
  });

  it("returns null when timestamp is in the future", () => {
    const future = mkPersisted({ timestamp: now + 1000 });
    const result = validatePersistedScene(future, PERSISTENCE_DEFAULTS, now);
    expect(result).toBeNull();
  });

  it("returns null for null input", () => {
    expect(validatePersistedScene(null, PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("returns null for non-object input", () => {
    expect(validatePersistedScene("hello", PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("returns null when timestamp is missing", () => {
    const bad = { ...mkPersisted(), timestamp: undefined };
    expect(validatePersistedScene(bad, PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("returns null when sceneName is missing", () => {
    const bad = { ...mkPersisted(), sceneName: undefined };
    expect(validatePersistedScene(bad, PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("returns null when glow is missing", () => {
    const bad = { ...mkPersisted(), glow: undefined };
    expect(validatePersistedScene(bad, PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("returns null when momentum is missing", () => {
    const bad = { ...mkPersisted(), momentum: undefined };
    expect(validatePersistedScene(bad, PERSISTENCE_DEFAULTS, now)).toBeNull();
  });

  it("accepts a scene right at the age boundary", () => {
    const atLimit = mkPersisted({ timestamp: now - PERSISTENCE_DEFAULTS.maxAgeMs });
    const result = validatePersistedScene(atLimit, PERSISTENCE_DEFAULTS, now);
    expect(result).not.toBeNull();
  });

  it("respects custom maxAgeMs", () => {
    const config = { ...PERSISTENCE_DEFAULTS, maxAgeMs: 1000 };
    const old = mkPersisted({ timestamp: now - 2000 });
    expect(validatePersistedScene(old, config, now)).toBeNull();

    const fresh = mkPersisted({ timestamp: now - 500 });
    expect(validatePersistedScene(fresh, config, now)).not.toBeNull();
  });
});

describe("rehydrateScene", () => {
  it("converts persisted scene to FusionScene", () => {
    const persisted: PersistedScene = {
      timestamp: Date.now(),
      sceneName: "apex",
      mode: "escalated",
      tone: "alert",
      posture: "sentinel",
      glow: 0.9,
      motion: 0.8,
      continuityBadge: { kind: "threshold", label: "10 sessions" },
      narrativeLine: "The field is at full height.",
      momentum: 0.8,
      timelinePhase: "peak",
    };

    const result = rehydrateScene(persisted);

    expect(result.sceneName).toBe("apex");
    expect(result.mode).toBe("escalated");
    expect(result.tone).toBe("alert");
    expect(result.posture).toBe("sentinel");
    expect(result.glow).toBe(0.9);
    expect(result.motion).toBe(0.8);
    expect(result.continuityBadge).toEqual({ kind: "threshold", label: "10 sessions" });
    expect(result.narrativeLine).toBe("The field is at full height.");
    expect(result.suppressAmbientPulse).toBe(false);
  });

  it("defaults continuityBadge to null if missing", () => {
    const persisted: PersistedScene = {
      timestamp: Date.now(),
      sceneName: "idle",
      mode: "resting",
      tone: "neutral",
      posture: "companion",
      glow: 0.3,
      motion: 0.5,
      continuityBadge: null,
      narrativeLine: null,
      momentum: 0,
      timelinePhase: "idle",
    };

    const result = rehydrateScene(persisted);
    expect(result.continuityBadge).toBeNull();
    expect(result.narrativeLine).toBeNull();
  });

  it("round-trips through serialize + validate + rehydrate", () => {
    const scene = mkScene();
    const timeline = mkTimeline();
    const now = Date.now();

    const serialized = serializeScene(scene, timeline, now);
    const validated = validatePersistedScene(serialized, PERSISTENCE_DEFAULTS, now);
    expect(validated).not.toBeNull();

    const rehydrated = rehydrateScene(validated!);

    expect(rehydrated.sceneName).toBe(scene.sceneName);
    expect(rehydrated.glow).toBe(scene.glow);
    expect(rehydrated.motion).toBe(scene.motion);
    expect(rehydrated.tone).toBe(scene.tone);
    expect(rehydrated.posture).toBe(scene.posture);
    expect(rehydrated.mode).toBe(scene.mode);
    expect(rehydrated.narrativeLine).toBe(scene.narrativeLine);
  });
});
