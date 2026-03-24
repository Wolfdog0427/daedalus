import { useMemo } from "react";
import type { OrchestratedScene } from "../shared/daedalus/sceneOrchestration";
import type { SceneSurfaceProps } from "../shared/daedalus/sceneSurfaces";
import { mapSceneToSurfaces, surfacesToCssVars } from "../shared/daedalus/sceneSurfacesEngine";

export interface SurfaceOutput {
  props: SceneSurfaceProps;
  cssVars: Record<string, string>;
}

/**
 * Derives concrete CSS-ready surface properties from an OrchestratedScene.
 * Returns both the typed props and a ready-to-spread CSS variable record.
 */
export function useSceneSurfaces(scene: OrchestratedScene): SurfaceOutput {
  return useMemo(() => {
    const props = mapSceneToSurfaces(scene);
    const cssVars = surfacesToCssVars(props);
    return { props, cssVars };
  }, [scene]);
}
