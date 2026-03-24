import { applySceneGrammar } from "../../shared/daedalus/sceneGrammarEngine";
import type { SceneGrammarState } from "../../shared/daedalus/sceneGrammar";
import { SCENE_GRAMMAR_DEFAULTS, makeInitialGrammarState } from "../../shared/daedalus/sceneGrammar";

function state(scene: string, enteredAt: number): SceneGrammarState {
  return { currentScene: scene as any, sceneEnteredAt: enteredAt };
}

describe("SceneGrammarEngine", () => {
  const T = 100_000;

  describe("same-scene transitions", () => {
    it("allows staying in the same scene with zero blend", () => {
      const { result } = applySceneGrammar("idle", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(true);
      expect(result.sceneName).toBe("idle");
      expect(result.blendMs).toBe(0);
    });
  });

  describe("natural arc transitions", () => {
    it("allows idle → focus", () => {
      const { result } = applySceneGrammar("focus", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.sceneName).toBe("focus");
      expect(result.blendMs).toBe(400);
    });

    it("allows focus → rising", () => {
      const { result } = applySceneGrammar("rising", state("focus", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.blendMs).toBe(500);
    });

    it("allows rising → apex with narrative sync", () => {
      const { result } = applySceneGrammar("apex", state("rising", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.blendMs).toBe(600);
      expect(result.narrativeSync).toBe(true);
    });

    it("allows apex → waning after dwell time", () => {
      const { result } = applySceneGrammar("waning", state("apex", T), SCENE_GRAMMAR_DEFAULTS, T + 1500);
      expect(result.allowed).toBe(true);
      expect(result.sceneName).toBe("waning");
      expect(result.blendMs).toBe(700);
    });

    it("blocks apex → waning before dwell time", () => {
      const { result } = applySceneGrammar("waning", state("apex", T), SCENE_GRAMMAR_DEFAULTS, T + 500);
      expect(result.allowed).toBe(false);
      expect(result.sceneName).toBe("apex");
    });

    it("allows waning → settling", () => {
      const { result } = applySceneGrammar("settling", state("waning", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.blendMs).toBe(600);
    });

    it("allows settling → idle", () => {
      const { result } = applySceneGrammar("idle", state("settling", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
    });
  });

  describe("alert overrides", () => {
    const scenes = ["idle", "focus", "rising", "apex", "waning", "settling", "celebrating", "exploring"] as const;

    for (const from of scenes) {
      it(`allows ${from} → alert with fast blend`, () => {
        const { result } = applySceneGrammar("alert", state(from, T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
        expect(result.allowed).toBe(true);
        expect(result.blendMs).toBe(200);
      });
    }

    it("allows alert → settling after dwell time", () => {
      const { result } = applySceneGrammar("settling", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
    });

    it("blocks alert → settling before dwell time", () => {
      const { result } = applySceneGrammar("settling", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 500);
      expect(result.allowed).toBe(false);
      expect(result.sceneName).toBe("alert");
    });
  });

  describe("forbidden transitions", () => {
    it("blocks apex → focus", () => {
      const { result } = applySceneGrammar("focus", state("apex", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
      expect(result.sceneName).toBe("apex");
    });

    it("blocks apex → idle", () => {
      const { result } = applySceneGrammar("idle", state("apex", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
    });

    it("blocks alert → apex", () => {
      const { result } = applySceneGrammar("apex", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
    });

    it("blocks alert → rising", () => {
      const { result } = applySceneGrammar("rising", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
    });

    it("blocks alert → celebrating", () => {
      const { result } = applySceneGrammar("celebrating", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
    });

    it("blocks alert → exploring", () => {
      const { result } = applySceneGrammar("exploring", state("alert", T), SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(result.allowed).toBe(false);
    });
  });

  describe("celebrating transitions", () => {
    it("allows idle → celebrating with narrative sync", () => {
      const { result } = applySceneGrammar("celebrating", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.narrativeSync).toBe(true);
    });

    it("blocks celebrating → idle before dwell", () => {
      const { result } = applySceneGrammar("idle", state("celebrating", T), SCENE_GRAMMAR_DEFAULTS, T + 500);
      expect(result.allowed).toBe(false);
    });

    it("allows celebrating → idle after dwell", () => {
      const { result } = applySceneGrammar("idle", state("celebrating", T), SCENE_GRAMMAR_DEFAULTS, T + 1500);
      expect(result.allowed).toBe(true);
    });
  });

  describe("exploring transitions", () => {
    it("allows idle → exploring", () => {
      const { result } = applySceneGrammar("exploring", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
    });

    it("allows exploring → focus", () => {
      const { result } = applySceneGrammar("focus", state("exploring", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
    });
  });

  describe("unlisted transitions", () => {
    it("allows unlisted transitions with default blend", () => {
      const { result } = applySceneGrammar("rising", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(result.allowed).toBe(true);
      expect(result.blendMs).toBe(SCENE_GRAMMAR_DEFAULTS.defaultBlendMs);
    });
  });

  describe("state tracking", () => {
    it("advances state on allowed transitions", () => {
      const { nextState } = applySceneGrammar("focus", state("idle", T), SCENE_GRAMMAR_DEFAULTS, T + 2000);
      expect(nextState.currentScene).toBe("focus");
      expect(nextState.sceneEnteredAt).toBe(T + 2000);
    });

    it("preserves state on blocked transitions", () => {
      const prev = state("apex", T);
      const { nextState } = applySceneGrammar("focus", prev, SCENE_GRAMMAR_DEFAULTS, T + 5000);
      expect(nextState).toBe(prev);
    });

    it("chains transitions correctly across multiple calls", () => {
      let s = makeInitialGrammarState();
      let now = 10000;

      const step = (to: string, dt: number) => {
        now += dt;
        const { result, nextState } = applySceneGrammar(to as any, s, SCENE_GRAMMAR_DEFAULTS, now);
        s = nextState;
        return result;
      };

      expect(step("focus", 1000).allowed).toBe(true);
      expect(step("rising", 1000).allowed).toBe(true);
      expect(step("apex", 1000).allowed).toBe(true);
      expect(step("waning", 500).allowed).toBe(false);
      expect(step("waning", 1000).allowed).toBe(true);
      expect(step("settling", 1000).allowed).toBe(true);
      expect(step("idle", 1000).allowed).toBe(true);
    });
  });
});
