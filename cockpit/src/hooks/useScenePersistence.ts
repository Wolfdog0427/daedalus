import { useEffect, useRef, useState } from "react";
import type { SceneFrame } from "../shared/daedalus/sceneSync";
import type { TimelineSnapshot } from "../shared/daedalus/timeline";
import type { PersistedScene } from "../shared/daedalus/scenePersistence";
import {
  SCENE_PERSISTENCE_ENABLED,
  PERSISTENCE_DEFAULTS,
} from "../shared/daedalus/scenePersistence";
import {
  serializeScene,
  validatePersistedScene,
} from "../shared/daedalus/scenePersistenceEngine";

export interface PersistenceInfo {
  restoredFrom: PersistedScene | null;
  ageMs: number | null;
}

/**
 * Persists the current scene frame to localStorage (debounced)
 * and restores the last saved scene on mount.
 *
 * Returns metadata about what was restored (if anything) for
 * display in the HUD.
 */
export function useScenePersistence(
  frame: SceneFrame,
  timeline: TimelineSnapshot,
): PersistenceInfo {
  const [info] = useState<PersistenceInfo>(() => {
    if (!SCENE_PERSISTENCE_ENABLED) return { restoredFrom: null, ageMs: null };

    try {
      const raw = localStorage.getItem(PERSISTENCE_DEFAULTS.storageKey);
      if (!raw) return { restoredFrom: null, ageMs: null };

      const parsed = JSON.parse(raw);
      const now = Date.now();
      const validated = validatePersistedScene(parsed, PERSISTENCE_DEFAULTS, now);
      if (!validated) return { restoredFrom: null, ageMs: null };

      return {
        restoredFrom: validated,
        ageMs: now - validated.timestamp,
      };
    } catch {
      return { restoredFrom: null, ageMs: null };
    }
  });

  const lastSaveRef = useRef(0);

  useEffect(() => {
    if (!SCENE_PERSISTENCE_ENABLED) return;

    const now = Date.now();
    if (now - lastSaveRef.current < PERSISTENCE_DEFAULTS.saveIntervalMs) return;

    lastSaveRef.current = now;
    const payload = serializeScene(frame.scene, timeline, now);

    try {
      localStorage.setItem(
        PERSISTENCE_DEFAULTS.storageKey,
        JSON.stringify(payload),
      );
    } catch {
      // localStorage full or unavailable — silently skip
    }
  }, [frame, timeline]);

  return info;
}
