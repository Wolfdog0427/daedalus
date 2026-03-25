/**
 * Daedalus Chat — Scoring-based Intent Classifier
 *
 * Multi-signal scorer with per-session context tracking:
 *   1. Exact phrase match (highest signal)
 *   2. Keyword token match
 *   3. Partial / substring overlap
 *   4. Context reinforcement from previous turn
 *
 * All state is held in ChatContext objects — no module-level globals.
 * The caller (ChatService) owns the session store.
 */

import { INTENT_DEFS, type IntentDef } from "./IntentDefinitions";

// ── Types ────────────────────────────────────────────────────────

export interface IntentResult {
  intent: string;
  confidence: number;
  topic: string;
}

export interface ChatContext {
  lastIntent: string | null;
  lastTopic: string | null;
  consecutiveUncertain: number;
}

// ── Scoring Constants ────────────────────────────────────────────

const CONFIDENCE_THRESHOLD = 0.25;
const CONTEXT_BOOST = 2.0;
const PHRASE_SCORE = 3.0;
const KEYWORD_SCORE = 1.5;
const PARTIAL_SCORE = 0.4;
const CONFIDENCE_DIVISOR = 10.0;

// ── Helpers ──────────────────────────────────────────────────────

export function normalize(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9\s''-]/g, "")
    .replace(/['']/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

function scoreIntent(
  normalized: string,
  tokens: string[],
  def: IntentDef,
  lastIntent: string | null,
): number {
  let score = 0;

  for (const phrase of def.phrases) {
    if (normalized.includes(phrase)) {
      score += PHRASE_SCORE;
    }
  }

  for (const kw of def.keywords) {
    if (tokens.includes(kw)) {
      score += KEYWORD_SCORE;
    } else if (normalized.includes(kw)) {
      score += PARTIAL_SCORE;
    }
  }

  if (def.name === lastIntent && score > 0) {
    score += CONTEXT_BOOST;
  }

  score *= def.weight;

  return score;
}

// ── Public API ───────────────────────────────────────────────────

export function createContext(): ChatContext {
  return { lastIntent: null, lastTopic: null, consecutiveUncertain: 0 };
}

/**
 * Classify an operator message into the best-matching intent.
 * Mutates `ctx` to track context for follow-ups.
 */
export function classifyIntent(input: string, ctx: ChatContext): IntentResult {
  const normalized = normalize(input);
  const tokens = tokenize(normalized);

  if (tokens.length === 0) {
    ctx.consecutiveUncertain++;
    return { intent: "uncertain", confidence: 0, topic: "" };
  }

  let bestIntent = "";
  let bestScore = 0;

  for (const def of INTENT_DEFS) {
    const s = scoreIntent(normalized, tokens, def, ctx.lastIntent);
    if (s > bestScore) {
      bestScore = s;
      bestIntent = def.name;
    }
  }

  const confidence = Math.min(1, bestScore / CONFIDENCE_DIVISOR);

  if (bestScore < CONFIDENCE_THRESHOLD || !bestIntent) {
    ctx.consecutiveUncertain++;
    return { intent: "uncertain", confidence, topic: normalized };
  }

  ctx.consecutiveUncertain = 0;
  // Do NOT overwrite ctx.lastIntent here — ChatService.processMessage
  // updates it after routing, so follow-up/clarification intents can
  // still read the *previous* turn's intent for chaining.

  return { intent: bestIntent, confidence, topic: normalized };
}
