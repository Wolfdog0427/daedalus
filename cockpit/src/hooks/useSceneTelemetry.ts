import { useState, useEffect, useRef } from "react";
import type { OrchestratedScene } from "../shared/daedalus/sceneOrchestration";
import type { GrammarResult } from "../shared/daedalus/sceneGrammar";
import type { TimelineSnapshot } from "../shared/daedalus/timeline";
import type { GovernorDisplayInfo } from "../shared/daedalus/governor";
import type { PersistenceInfo } from "./useScenePersistence";
import type { TelemetryEvent, TelemetryEventType } from "../shared/daedalus/sceneTelemetry";
import { SCENE_TELEMETRY_ENABLED, TELEMETRY_DEFAULTS } from "../shared/daedalus/sceneTelemetry";
import { createTelemetryEvent, appendToBuffer } from "../shared/daedalus/sceneTelemetryEngine";

export interface TelemetryInputs {
  scene: OrchestratedScene;
  grammar: GrammarResult;
  timeline: TimelineSnapshot;
  governorDisplay: GovernorDisplayInfo;
  persistence: PersistenceInfo;
}

interface PrevSnapshot {
  sceneName: string;
  progress: number;
  timelinePhase: string;
  narrativeLine: string | null;
  escalationLocked: boolean;
  modeCooldown: boolean;
  toneCooldown: boolean;
  grammarAllowed: boolean;
}

/**
 * Observes the expressive pipeline and records telemetry events
 * when meaningful state transitions occur (edges, not levels).
 *
 * Returns the rolling event buffer for HUD display.
 */
export function useSceneTelemetry(inputs: TelemetryInputs): TelemetryEvent[] {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const idRef = useRef(0);
  const mountedRef = useRef(false);
  const prevRef = useRef<PrevSnapshot>({
    sceneName: inputs.scene.sceneName,
    progress: inputs.scene.progress,
    timelinePhase: inputs.timeline.phase,
    narrativeLine: inputs.scene.narrativeLine,
    escalationLocked: inputs.governorDisplay.escalationLocked,
    modeCooldown: inputs.governorDisplay.modeCooldownActive,
    toneCooldown: inputs.governorDisplay.toneCooldownActive,
    grammarAllowed: inputs.grammar.allowed,
  });

  useEffect(() => {
    if (!SCENE_TELEMETRY_ENABLED) return;

    const prev = prevRef.current;
    const batch: TelemetryEvent[] = [];
    const now = Date.now();

    function record(type: TelemetryEventType, payload: Record<string, unknown>) {
      idRef.current += 1;
      batch.push(createTelemetryEvent(type, payload, idRef.current, now));
    }

    // ── First render: persistence restore ──
    if (!mountedRef.current) {
      mountedRef.current = true;
      if (inputs.persistence.restoredFrom) {
        record("persistence-restore", {
          scene: inputs.persistence.restoredFrom.sceneName,
          ageMs: inputs.persistence.ageMs,
        });
      }
    }

    // ── Scene transition ──
    if (inputs.scene.sceneName !== prev.sceneName) {
      record("scene-transition", {
        from: prev.sceneName,
        to: inputs.scene.sceneName,
        blendMs: inputs.grammar.blendMs,
      });
    }

    // ── Grammar rejection (rising edge) ──
    if (!inputs.grammar.allowed && prev.grammarAllowed) {
      record("scene-rejected", { held: inputs.grammar.sceneName });
    }

    // ── Blend start (progress drops below 1) ──
    if (inputs.scene.progress < 1 && prev.progress >= 1) {
      record("blend-start", {
        scene: inputs.scene.sceneName,
        blendMs: inputs.scene.blendMs,
      });
    }

    // ── Blend complete (progress reaches 1) ──
    if (inputs.scene.progress >= 1 && prev.progress < 1) {
      record("blend-complete", { scene: inputs.scene.sceneName });
    }

    // ── Timeline phase change ──
    if (inputs.timeline.phase !== prev.timelinePhase) {
      record("momentum", {
        prevPhase: prev.timelinePhase,
        phase: inputs.timeline.phase,
        momentum: inputs.timeline.momentum,
      });
    }

    // ── Narrative emission (new non-null line) ──
    if (
      inputs.scene.narrativeLine &&
      inputs.scene.narrativeLine !== prev.narrativeLine
    ) {
      record("narrative", { line: inputs.scene.narrativeLine });
    }

    // ── Governor escalation lock (rising edge) ──
    if (inputs.governorDisplay.escalationLocked && !prev.escalationLocked) {
      record("governor-lock", {});
    }

    // ── Governor cooldown (rising edge on either) ──
    if (
      (inputs.governorDisplay.modeCooldownActive && !prev.modeCooldown) ||
      (inputs.governorDisplay.toneCooldownActive && !prev.toneCooldown)
    ) {
      record("governor-cooldown", {
        mode: inputs.governorDisplay.modeCooldownActive,
        tone: inputs.governorDisplay.toneCooldownActive,
      });
    }

    // ── Update snapshot ──
    prevRef.current = {
      sceneName: inputs.scene.sceneName,
      progress: inputs.scene.progress,
      timelinePhase: inputs.timeline.phase,
      narrativeLine: inputs.scene.narrativeLine,
      escalationLocked: inputs.governorDisplay.escalationLocked,
      modeCooldown: inputs.governorDisplay.modeCooldownActive,
      toneCooldown: inputs.governorDisplay.toneCooldownActive,
      grammarAllowed: inputs.grammar.allowed,
    };

    if (batch.length > 0) {
      setEvents((prev) => appendToBuffer(prev, batch, TELEMETRY_DEFAULTS));
    }
  });

  return events;
}
