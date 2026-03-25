/**
 * Tests for the Daedalus Chat intent classification system.
 *
 * Covers:
 *  - Status synonyms
 *  - Acknowledgment handling
 *  - Follow-up / context tracking
 *  - Identity queries
 *  - False-positive prevention
 *  - Fallback / uncertainty
 *  - Context reinforcement
 *  - Greeting
 *  - Clarification
 *  - Expanded intent coverage
 */

import { classifyIntent, getLastIntent, resetContext } from "../orchestrator/chat/IntentClassifier";
import { getFallbackMessage, resetFallbackIndex } from "../orchestrator/chat/FallbackVariation";

beforeEach(() => {
  resetContext();
  resetFallbackIndex();
});

describe("Status synonyms", () => {
  const statusInputs = [
    "status",
    "what's going on",
    "how are you",
    "how is everything",
    "is everything okay",
    "give me an overview",
    "give me a summary",
    "how's it going",
    "status report",
    "what is the situation",
    "system health",
    "are you alive",
    "what should I know",
    "how is the system",
    "are we good",
    "overview",
    "summary",
    "update",
    "fill me in",
    "catch me up",
    "current state",
    "bring me up to speed",
  ];

  for (const input of statusInputs) {
    it(`classifies "${input}" as status`, () => {
      const result = classifyIntent(input);
      expect(result.intent).toBe("status");
      expect(result.confidence).toBeGreaterThan(0);
    });
  }
});

describe("Acknowledgment handling", () => {
  const ackInputs = [
    "thanks",
    "thank you",
    "ok",
    "got it",
    "perfect",
    "sounds good",
    "understood",
    "cool",
    "nice",
    "awesome",
    "great",
    "makes sense",
    "much appreciated",
  ];

  for (const input of ackInputs) {
    it(`classifies "${input}" as acknowledgment`, () => {
      const result = classifyIntent(input);
      expect(result.intent).toBe("acknowledgment");
    });
  }
});

describe("Follow-up and context tracking", () => {
  it("classifies follow-up phrases", () => {
    classifyIntent("show me the status");

    const follow = classifyIntent("tell me more");
    expect(follow.intent).toBe("followup");
  });

  it("stores lastIntent after a real query", () => {
    classifyIntent("what is the current strategy?");
    expect(getLastIntent()).toBe("strategy");
  });

  const followUpPhrases = [
    "tell me more",
    "go on",
    "elaborate",
    "what else",
    "more details",
    "expand on that",
    "can you elaborate",
  ];

  for (const phrase of followUpPhrases) {
    it(`recognizes follow-up: "${phrase}"`, () => {
      classifyIntent("status");
      const result = classifyIntent(phrase);
      expect(result.intent).toBe("followup");
    });
  }
});

describe("Identity queries", () => {
  const identityInputs = [
    "who are you",
    "what are you",
    "describe yourself",
    "your identity",
    "tell me about you",
    "what is daedalus",
    "introduce yourself",
  ];

  for (const input of identityInputs) {
    it(`classifies "${input}" as identity`, () => {
      const result = classifyIntent(input);
      expect(result.intent).toBe("identity");
    });
  }
});

describe("False-positive prevention", () => {
  it("does NOT classify bare 'change' as rollback", () => {
    const result = classifyIntent("I want to change the setting");
    expect(result.intent).not.toBe("rollback");
  });

  it("does NOT classify bare 'critical' as escalation", () => {
    const result = classifyIntent("that is critical information");
    expect(result.intent).not.toBe("escalation");
  });

  it("does NOT classify bare 'being' as constitution", () => {
    const result = classifyIntent("I love being here");
    expect(result.intent).not.toBe("constitution");
  });

  it("does NOT classify bare 'log' as history", () => {
    const result = classifyIntent("I need to log something");
    expect(result.intent).not.toBe("history");
  });

  it("does NOT classify bare 'event' as history", () => {
    const result = classifyIntent("what a nice event");
    expect(result.intent).not.toBe("history");
  });

  it("does NOT classify bare 'problem' as incidents", () => {
    const result = classifyIntent("that's not a problem");
    expect(result.intent).not.toBe("incidents");
  });

  it("does NOT classify bare 'identity' as trust", () => {
    const result = classifyIntent("your identity");
    expect(result.intent).not.toBe("trust");
  });
});

describe("Fallback / uncertainty", () => {
  it("returns uncertain for gibberish", () => {
    const result = classifyIntent("asdfghjkl");
    expect(result.intent).toBe("uncertain");
  });

  it("returns uncertain for random sentence", () => {
    const result = classifyIntent("the weather is lovely today");
    expect(result.intent).toBe("uncertain");
  });

  it("returns uncertain for empty-ish input", () => {
    const result = classifyIntent("   ");
    expect(result.intent).toBe("uncertain");
  });

  it("consecutive uncertain calls don't crash", () => {
    classifyIntent("xyz");
    classifyIntent("abc");
    const result = classifyIntent("qqq");
    expect(result.intent).toBe("uncertain");
  });
});

describe("Context reinforcement", () => {
  it("prior intent boosts scoring on ambiguous input", () => {
    classifyIntent("show me the node fleet");
    expect(getLastIntent()).toBe("nodes");

    const result = classifyIntent("fleet");
    expect(result.intent).toBe("nodes");
  });
});

describe("Greeting", () => {
  for (const g of ["hello", "hi", "hey", "greetings", "yo", "good morning"]) {
    it(`classifies "${g}" as greeting`, () => {
      const result = classifyIntent(g);
      expect(result.intent).toBe("greeting");
    });
  }
});

describe("Clarification", () => {
  for (const c of ["what do you mean", "i don't understand", "can you clarify", "clarify that"]) {
    it(`classifies "${c}" as clarification`, () => {
      const result = classifyIntent(c);
      expect(result.intent).toBe("clarification");
    });
  }
});

describe("Specific intent coverage", () => {
  const cases: [string, string][] = [
    ["show me the strategy", "strategy"],
    ["alignment breakdown", "strategy"],
    ["operator trust", "trust"],
    ["who am i", "trust"],
    ["node status", "nodes"],
    ["fleet health", "nodes"],
    ["safe mode", "safemode"],
    ["constitutional freeze", "safemode"],
    ["regulation loop", "regulation"],
    ["drift status", "regulation"],
    ["governance posture", "governance"],
    ["show governance", "governance"],
    ["escalation status", "escalation"],
    ["show escalations", "escalation"],
    ["any errors", "incidents"],
    ["any incidents", "incidents"],
    ["help", "help"],
    ["what can you do", "help"],
    ["event history", "history"],
    ["show history", "history"],
    ["constitution status", "constitution"],
    ["show constitution", "constitution"],
    ["approval gate", "approval"],
    ["auto-approval", "approval"],
    ["rollback registry", "rollback"],
    ["undo last change", "rollback"],
  ];

  for (const [input, expected] of cases) {
    it(`"${input}" → ${expected}`, () => {
      resetContext();
      const result = classifyIntent(input);
      expect(result.intent).toBe(expected);
    });
  }
});

describe("classifyIntent return shape", () => {
  it("returns intent, confidence, and topic", () => {
    const result = classifyIntent("status");
    expect(result).toHaveProperty("intent");
    expect(result).toHaveProperty("confidence");
    expect(result).toHaveProperty("topic");
    expect(typeof result.intent).toBe("string");
    expect(typeof result.confidence).toBe("number");
    expect(typeof result.topic).toBe("string");
  });

  it("uncertain result has confidence < 1", () => {
    const result = classifyIntent("xyzzy");
    expect(result.intent).toBe("uncertain");
    expect(result.confidence).toBeLessThan(1);
  });
});

describe("Fallback variation generator", () => {
  it("returns a string on each call", () => {
    const msg = getFallbackMessage();
    expect(typeof msg).toBe("string");
    expect(msg.length).toBeGreaterThan(0);
  });

  it("rotates through different messages", () => {
    const seen = new Set<string>();
    for (let i = 0; i < 5; i++) {
      seen.add(getFallbackMessage());
    }
    expect(seen.size).toBe(5);
  });

  it("cycles back after exhausting all templates", () => {
    const first = getFallbackMessage();
    for (let i = 0; i < 4; i++) getFallbackMessage();
    const cycled = getFallbackMessage();
    expect(cycled).toBe(first);
  });

  it("never returns the same message twice in a row", () => {
    let prev = getFallbackMessage();
    for (let i = 0; i < 10; i++) {
      const next = getFallbackMessage();
      expect(next).not.toBe(prev);
      prev = next;
    }
  });

  it("resetFallbackIndex restarts the rotation", () => {
    const first = getFallbackMessage();
    getFallbackMessage();
    resetFallbackIndex();
    const afterReset = getFallbackMessage();
    expect(afterReset).toBe(first);
  });
});
