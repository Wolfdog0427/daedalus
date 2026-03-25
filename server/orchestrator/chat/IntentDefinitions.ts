/**
 * Daedalus Chat — Intent Definitions
 *
 * Each intent has keywords (single tokens that score), phrases (multi-word
 * patterns that score higher), and a base weight.  The scoring classifier
 * uses these to rank intents by relevance instead of first-match regex.
 */

export interface IntentDef {
  name: string;
  keywords: string[];
  phrases: string[];
  weight: number;
}

export const INTENT_DEFS: IntentDef[] = [
  // ── Greeting ──────────────────────────────────────────────
  {
    name: "greeting",
    keywords: ["hi", "hello", "hey", "greetings", "yo", "sup", "howdy", "hiya"],
    phrases: ["good morning", "good afternoon", "good evening"],
    weight: 1.0,
  },

  // ── Identity (who is Daedalus) ────────────────────────────
  {
    name: "identity",
    keywords: [],
    phrases: [
      "who are you", "what are you", "about yourself", "your name",
      "tell me about you", "describe yourself", "what is daedalus",
      "your identity", "introduce yourself", "what do you do",
      "your purpose", "what is your purpose",
    ],
    weight: 1.2,
  },

  // ── Status (broad system overview) ────────────────────────
  {
    name: "status",
    keywords: ["status", "report", "overview", "summary", "situation", "update", "sitrep", "dashboard"],
    phrases: [
      "how are you", "how's it going", "how is it going", "how are things",
      "how is everything", "how's everything", "is everything okay",
      "is everything ok", "is everything alright", "what's going on",
      "whats going on", "what is going on", "what's happening",
      "what is happening", "what's the situation", "what is the situation",
      "give me an overview", "give me a summary", "give me a report",
      "status report", "system status", "system state",
      "how is the system", "how's the system", "are you okay",
      "are you running", "are you up", "are you alive",
      "are you working", "is the system healthy", "system health",
      "are you running properly", "what should i know",
      "anything i should worry about", "fill me in",
      "what's up", "whats up", "what is up", "catch me up",
      "bring me up to speed", "current state",
      "how is the system doing", "how are things looking",
      "is everything running", "are we good",
    ],
    weight: 1.0,
  },

  // ── Strategy / Alignment ──────────────────────────────────
  {
    name: "strategy",
    keywords: ["strategy", "alignment", "sovereignty", "confidence"],
    phrases: [
      "alignment score", "alignment breakdown", "alignment status",
      "how is alignment", "how's alignment", "current strategy",
      "strategy evaluation", "show alignment", "alignment report",
      "alignment breakdown", "how aligned", "is alignment okay",
    ],
    weight: 1.0,
  },

  // ── Operator Trust ────────────────────────────────────────
  {
    name: "trust",
    keywords: ["calibrated", "calibration"],
    phrases: [
      "operator trust", "trust score", "trust level", "trust status",
      "who am i", "am i bound", "am i trusted", "operator identity",
      "my trust", "operator status", "operator posture",
      "show trust", "trust axes", "trust breakdown",
    ],
    weight: 1.0,
  },

  // ── Nodes / Fleet ─────────────────────────────────────────
  {
    name: "nodes",
    keywords: ["fleet", "fabric", "mirror", "quarantine", "quarantined"],
    phrases: [
      "node status", "fleet status", "fleet health", "show nodes",
      "how are the nodes", "how many nodes", "node count",
      "node health", "show fleet", "node fabric",
    ],
    weight: 1.0,
  },

  // ── Safe Mode / Freeze ────────────────────────────────────
  {
    name: "safemode",
    keywords: [],
    phrases: [
      "safe mode", "safemode", "constitutional freeze", "freeze mode",
      "is safe mode on", "is safe mode active", "am i safe",
      "is it safe", "are we safe", "safety status",
    ],
    weight: 1.1,
  },

  // ── Regulation ────────────────────────────────────────────
  {
    name: "regulation",
    keywords: ["regulation", "microcorrection", "macrocorrection"],
    phrases: [
      "regulation loop", "micro correction", "macro correction",
      "alignment drift", "drift status", "drift metrics",
      "show regulation", "regulation status", "how is regulation",
      "alignment regulation",
    ],
    weight: 1.0,
  },

  // ── Governance ────────────────────────────────────────────
  {
    name: "governance",
    keywords: ["governance", "posture", "override", "overrides"],
    phrases: [
      "governance posture", "governance status", "show governance",
      "governance overrides", "governance votes", "governance state",
    ],
    weight: 1.0,
  },

  // ── Escalation ────────────────────────────────────────────
  {
    name: "escalation",
    keywords: ["escalation", "escalations"],
    phrases: [
      "escalation status", "show escalations", "escalation level",
      "any escalations", "current escalation", "is there an escalation",
      "warning level", "alert level", "any alerts", "any warnings",
    ],
    weight: 1.0,
  },

  // ── Incidents / Errors ────────────────────────────────────
  {
    name: "incidents",
    keywords: ["incident", "incidents"],
    phrases: [
      "any errors", "any problems", "any issues", "any incidents",
      "show errors", "show incidents", "error count", "incident report",
      "what's wrong", "what is wrong", "is something wrong",
      "is anything wrong", "something broken", "any bugs",
    ],
    weight: 1.0,
  },

  // ── Help ──────────────────────────────────────────────────
  {
    name: "help",
    keywords: ["help", "commands", "abilities"],
    phrases: [
      "what can you do", "what can you help with", "show commands",
      "what do you know", "your capabilities", "how to use",
    ],
    weight: 1.0,
  },

  // ── History / Events ──────────────────────────────────────
  {
    name: "history",
    keywords: ["timeline"],
    phrases: [
      "event history", "show history", "recent events", "event log",
      "system history", "show events", "show timeline",
      "what happened recently", "recent activity",
    ],
    weight: 1.0,
  },

  // ── Constitution ──────────────────────────────────────────
  {
    name: "constitution",
    keywords: ["constitution", "invariant", "invariants"],
    phrases: [
      "constitution status", "show constitution", "being constitution",
      "constitutional checks", "invariant checks", "being validation",
    ],
    weight: 1.0,
  },

  // ── Approval Gate ─────────────────────────────────────────
  {
    name: "approval",
    keywords: [],
    phrases: [
      "auto approval", "auto-approval", "approval gate", "approval status",
      "show approval", "approval config", "approval threshold",
    ],
    weight: 1.0,
  },

  // ── Rollback / Registry ───────────────────────────────────
  {
    name: "rollback",
    keywords: ["rollback", "rollbacks"],
    phrases: [
      "rollback registry", "rollback status", "show rollbacks",
      "undo last change", "revert config", "tracked changes",
      "change registry", "show registry",
    ],
    weight: 1.0,
  },

  // ── Acknowledgment ────────────────────────────────────────
  {
    name: "acknowledgment",
    keywords: ["thanks", "thank", "thankyou", "ok", "okay", "understood", "cool", "nice", "great", "awesome", "sweet"],
    phrases: [
      "thank you", "got it", "makes sense", "that helps",
      "good to know", "i see", "alright", "perfect", "sounds good",
      "much appreciated", "appreciate it", "all good",
    ],
    weight: 1.3,
  },

  // ── Follow-up ─────────────────────────────────────────────
  {
    name: "followup",
    keywords: ["elaborate", "more", "details"],
    phrases: [
      "tell me more", "go on", "what else", "explain that",
      "can you elaborate", "more details", "expand on that",
      "keep going", "continue", "and then", "what about that",
      "dig deeper", "more info", "more information",
    ],
    weight: 1.4,
  },

  // ── Clarification (operator is confused) ──────────────────
  {
    name: "clarification",
    keywords: [],
    phrases: [
      "what do you mean", "i dont understand", "i don't understand",
      "not sure what you mean", "can you clarify", "clarify that",
      "that doesnt make sense", "that doesn't make sense",
      "explain what you mean",
    ],
    weight: 1.3,
  },
];
