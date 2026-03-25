/**
 * Tests for the Daedalus Chat intent classification system.
 *
 * Covers:
 *  - Status synonyms (broad)
 *  - Safemode
 *  - Acknowledgment handling + short human replies
 *  - Follow-up / context tracking with expanded=true re-routing
 *  - Identity queries (NOT trust)
 *  - False-positive prevention (change, critical, being, log, event)
 *  - Fallback / uncertainty (no raw stats)
 *  - Context reinforcement across turns
 *  - Per-session context isolation
 *  - Greeting, Clarification
 *  - Expanded intent coverage for all domains
 *  - classifyIntent return shape { intent, confidence, topic }
 *  - Fallback variation generator
 *  - getChatHelp() structure
 */

import {
  classifyIntent,
  createContext,
  type ChatContext,
} from "../orchestrator/chat/IntentClassifier";
import { getFallbackMessage, resetFallbackIndex } from "../orchestrator/chat/FallbackVariation";
import { getChatHelp } from "../orchestrator/chat/ChatService";
import { INTENT_DEFS } from "../orchestrator/chat/IntentDefinitions";

let ctx: ChatContext;

beforeEach(() => {
  ctx = createContext();
  resetFallbackIndex();
});

// ═══════════════════════════════════════════════════════════════
// STATUS SYNONYMS
// ═══════════════════════════════════════════════════════════════

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
    "update me",
    "is everything running",
    "are you working",
    "how are things looking",
  ];

  for (const input of statusInputs) {
    it(`classifies "${input}" as status`, () => {
      const result = classifyIntent(input, ctx);
      expect(result.intent).toBe("status");
      expect(result.confidence).toBeGreaterThan(0);
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// SAFEMODE
// ═══════════════════════════════════════════════════════════════

describe("Safemode", () => {
  for (const input of ["am I safe", "is it safe", "are we safe", "safe mode", "safety status"]) {
    it(`classifies "${input}" as safemode`, () => {
      const result = classifyIntent(input, ctx);
      expect(result.intent).toBe("safemode");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// ACKNOWLEDGMENT
// ═══════════════════════════════════════════════════════════════

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
      const result = classifyIntent(input, ctx);
      expect(result.intent).toBe("acknowledgment");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// FOLLOW-UP AND CONTEXT TRACKING
// ═══════════════════════════════════════════════════════════════

describe("Follow-up and context tracking", () => {
  it("classifies follow-up phrases", () => {
    classifyIntent("show me the status", ctx);
    const follow = classifyIntent("tell me more", ctx);
    expect(follow.intent).toBe("followup");
  });

  it("returns correct intent for a real query (lastIntent set by ChatService)", () => {
    const result = classifyIntent("what is the current strategy?", ctx);
    expect(result.intent).toBe("strategy");
    // classifyIntent no longer sets lastIntent — ChatService.processMessage does
    // to prevent follow-up routing from seeing overwritten state
  });

  it("does not overwrite lastIntent on uncertain", () => {
    ctx.lastIntent = "status";
    classifyIntent("xyzzy gibberish", ctx);
    expect(ctx.lastIntent).toBe("status");
  });

  const followUpPhrases = [
    "tell me more",
    "go on",
    "elaborate",
    "what else",
    "more details",
    "expand on that",
    "can you elaborate",
    "why",
    "explain",
  ];

  for (const phrase of followUpPhrases) {
    it(`recognizes follow-up: "${phrase}"`, () => {
      classifyIntent("status", ctx);
      const result = classifyIntent(phrase, ctx);
      expect(result.intent).toBe("followup");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// IDENTITY QUERIES
// ═══════════════════════════════════════════════════════════════

describe("Identity queries", () => {
  const identityInputs = [
    "who are you",
    "what are you",
    "describe yourself",
    "your identity",
    "tell me about you",
    "what is daedalus",
    "introduce yourself",
    "what is your identity as a system",
    "what is your purpose",
  ];

  for (const input of identityInputs) {
    it(`classifies "${input}" as identity`, () => {
      const result = classifyIntent(input, ctx);
      expect(result.intent).toBe("identity");
    });
  }

  it("classifies 'what is your identity as a system?' as identity, NOT trust", () => {
    const result = classifyIntent("what is your identity as a system?", ctx);
    expect(result.intent).toBe("identity");
    expect(result.intent).not.toBe("trust");
  });
});

// ═══════════════════════════════════════════════════════════════
// FALSE-POSITIVE PREVENTION
// ═══════════════════════════════════════════════════════════════

describe("False-positive prevention", () => {
  it("'I want to make a change to the config' does NOT match rollback", () => {
    const result = classifyIntent("I want to make a change to the config", ctx);
    expect(result.intent).not.toBe("rollback");
  });

  it("'That is a critical feature' does NOT match escalation", () => {
    const result = classifyIntent("That is a critical feature", ctx);
    expect(result.intent).not.toBe("escalation");
  });

  it("'I love being here' does NOT match constitution", () => {
    const result = classifyIntent("I love being here", ctx);
    expect(result.intent).not.toBe("constitution");
  });

  it("'Let me log in first' does NOT match history", () => {
    const result = classifyIntent("Let me log in first", ctx);
    expect(result.intent).not.toBe("history");
  });

  it("'what a nice event' does NOT match history", () => {
    const result = classifyIntent("what a nice event", ctx);
    expect(result.intent).not.toBe("history");
  });

  it("'that's not a problem' does NOT match incidents", () => {
    const result = classifyIntent("that's not a problem", ctx);
    expect(result.intent).not.toBe("incidents");
  });

  it("'your identity' matches identity, NOT trust", () => {
    const result = classifyIntent("your identity", ctx);
    expect(result.intent).not.toBe("trust");
    expect(result.intent).toBe("identity");
  });

  it("'I want to change the setting' does NOT match rollback", () => {
    const result = classifyIntent("I want to change the setting", ctx);
    expect(result.intent).not.toBe("rollback");
  });
});

// ═══════════════════════════════════════════════════════════════
// FALLBACK / UNCERTAINTY
// ═══════════════════════════════════════════════════════════════

describe("Fallback / uncertainty", () => {
  it("returns uncertain for gibberish", () => {
    const result = classifyIntent("asdfghjkl", ctx);
    expect(result.intent).toBe("uncertain");
  });

  it("returns uncertain for random sentence", () => {
    const result = classifyIntent("the weather is lovely today", ctx);
    expect(result.intent).toBe("uncertain");
  });

  it("returns uncertain for empty-ish input", () => {
    const result = classifyIntent("   ", ctx);
    expect(result.intent).toBe("uncertain");
  });

  it("consecutive uncertain calls don't crash and track count", () => {
    classifyIntent("xyz", ctx);
    classifyIntent("abc", ctx);
    const result = classifyIntent("qqq", ctx);
    expect(result.intent).toBe("uncertain");
    expect(ctx.consecutiveUncertain).toBe(3);
  });

  it("fallback messages do not contain raw system stats", () => {
    for (let i = 0; i < 5; i++) {
      const msg = getFallbackMessage();
      expect(msg).not.toMatch(/alignment.*\d+%/);
      expect(msg).not.toMatch(/trustScore/);
      expect(msg).not.toMatch(/\d+ nodes/);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// CONTEXT REINFORCEMENT
// ═══════════════════════════════════════════════════════════════

describe("Context reinforcement", () => {
  it("prior intent boosts scoring on ambiguous input", () => {
    const first = classifyIntent("show me the node fleet", ctx);
    expect(first.intent).toBe("nodes");
    // Simulate ChatService setting lastIntent after routing
    ctx.lastIntent = first.intent;

    const result = classifyIntent("fleet", ctx);
    expect(result.intent).toBe("nodes");
  });

  it("ask status then 'tell me more' → followup detected, previous lastIntent was status", () => {
    const first = classifyIntent("give me a status report", ctx);
    expect(first.intent).toBe("status");
    // Simulate ChatService setting lastIntent after routing
    ctx.lastIntent = first.intent;

    const prevIntent = ctx.lastIntent;
    const result = classifyIntent("tell me more", ctx);
    expect(result.intent).toBe("followup");
    expect(prevIntent).toBe("status");
  });
});

// ═══════════════════════════════════════════════════════════════
// PER-SESSION ISOLATION
// ═══════════════════════════════════════════════════════════════

describe("Per-session context isolation", () => {
  it("two sessions have independent context", () => {
    const ctxA = createContext();
    const ctxB = createContext();

    const resultA = classifyIntent("show me the strategy", ctxA);
    const resultB = classifyIntent("node status", ctxB);

    expect(resultA.intent).toBe("strategy");
    expect(resultB.intent).toBe("nodes");
  });

  it("uncertain in one session does not affect another", () => {
    const ctxA = createContext();
    const ctxB = createContext();

    classifyIntent("xyzzy", ctxA);
    const resultB = classifyIntent("status", ctxB);

    expect(ctxA.consecutiveUncertain).toBe(1);
    expect(ctxB.consecutiveUncertain).toBe(0);
    expect(resultB.intent).toBe("status");
  });
});

// ═══════════════════════════════════════════════════════════════
// GREETING
// ═══════════════════════════════════════════════════════════════

describe("Greeting", () => {
  for (const g of ["hello", "hi", "hey", "greetings", "yo", "good morning"]) {
    it(`classifies "${g}" as greeting`, () => {
      const result = classifyIntent(g, ctx);
      expect(result.intent).toBe("greeting");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// CLARIFICATION
// ═══════════════════════════════════════════════════════════════

describe("Clarification", () => {
  for (const c of [
    "what do you mean",
    "i don't understand",
    "can you clarify",
    "clarify that",
    "explain that again",
    "i'm not sure",
  ]) {
    it(`classifies "${c}" as clarification`, () => {
      const result = classifyIntent(c, ctx);
      expect(result.intent).toBe("clarification");
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// SPECIFIC INTENT COVERAGE
// ═══════════════════════════════════════════════════════════════

describe("Specific intent coverage", () => {
  const cases: [string, string][] = [
    ["show me the strategy", "strategy"],
    ["alignment breakdown", "strategy"],
    ["operator trust", "trust"],
    ["who am i", "trust"],
    ["show me trust", "trust"],
    ["trust posture", "trust"],
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
    ["recent incidents", "incidents"],
    ["help", "help"],
    ["what can you do", "help"],
    ["event history", "history"],
    ["show history", "history"],
    ["show me the history", "history"],
    ["constitution status", "constitution"],
    ["show constitution", "constitution"],
    ["constitution check", "constitution"],
    ["approval gate", "approval"],
    ["auto-approval", "approval"],
    ["rollback registry", "rollback"],
    ["rollback", "rollback"],
    ["undo last change", "rollback"],
    ["revert config", "rollback"],
    ["revert configuration", "rollback"],
  ];

  for (const [input, expected] of cases) {
    it(`"${input}" → ${expected}`, () => {
      const fresh = createContext();
      const result = classifyIntent(input, fresh);
      expect(result.intent).toBe(expected);
    });
  }
});

// ═══════════════════════════════════════════════════════════════
// RETURN SHAPE
// ═══════════════════════════════════════════════════════════════

describe("classifyIntent return shape", () => {
  it("returns { intent, confidence, topic }", () => {
    const result = classifyIntent("status", ctx);
    expect(result).toHaveProperty("intent");
    expect(result).toHaveProperty("confidence");
    expect(result).toHaveProperty("topic");
    expect(typeof result.intent).toBe("string");
    expect(typeof result.confidence).toBe("number");
    expect(typeof result.topic).toBe("string");
  });

  it("uncertain result has confidence < 1", () => {
    const result = classifyIntent("xyzzy", ctx);
    expect(result.intent).toBe("uncertain");
    expect(result.confidence).toBeLessThan(1);
  });

  it("confident result has confidence > 0", () => {
    const result = classifyIntent("give me a status report", ctx);
    expect(result.intent).toBe("status");
    expect(result.confidence).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// FALLBACK VARIATION GENERATOR
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// CHAT HELP STRUCTURE
// ═══════════════════════════════════════════════════════════════

describe("getChatHelp()", () => {
  it("returns an intents array", () => {
    const help = getChatHelp();
    expect(help).toHaveProperty("intents");
    expect(Array.isArray(help.intents)).toBe(true);
    expect(help.intents.length).toBeGreaterThan(0);
  });

  it("each entry has name, description, and examples", () => {
    const help = getChatHelp();
    for (const entry of help.intents) {
      expect(typeof entry.name).toBe("string");
      expect(typeof entry.description).toBe("string");
      expect(Array.isArray(entry.examples)).toBe(true);
      expect(entry.examples.length).toBeGreaterThan(0);
    }
  });

  it("includes status, trust, nodes, governance, incidents, identity", () => {
    const help = getChatHelp();
    const names = help.intents.map(e => e.name);
    expect(names).toContain("status");
    expect(names).toContain("trust");
    expect(names).toContain("nodes");
    expect(names).toContain("governance");
    expect(names).toContain("incidents");
    expect(names).toContain("identity");
    expect(names).toContain("safemode");
  });

  it("does NOT expose internal intents (greeting, ack, followup, clarification)", () => {
    const help = getChatHelp();
    const names = help.intents.map(e => e.name);
    expect(names).not.toContain("greeting");
    expect(names).not.toContain("acknowledgment");
    expect(names).not.toContain("followup");
    expect(names).not.toContain("clarification");
  });
});

// ═══════════════════════════════════════════════════════════════
// INTENT DEFINITIONS STRUCTURE
// ═══════════════════════════════════════════════════════════════

describe("IntentDef structure", () => {
  it("every intent has name, keywords, phrases, weight, description, examples", () => {
    for (const def of INTENT_DEFS) {
      expect(typeof def.name).toBe("string");
      expect(Array.isArray(def.keywords)).toBe(true);
      expect(Array.isArray(def.phrases)).toBe(true);
      expect(typeof def.weight).toBe("number");
      expect(def.weight).toBeGreaterThan(0);
      expect(typeof def.description).toBe("string");
      expect(Array.isArray(def.examples)).toBe(true);
    }
  });

  it("no duplicate intent names", () => {
    const names = INTENT_DEFS.map(d => d.name);
    expect(new Set(names).size).toBe(names.length);
  });
});
