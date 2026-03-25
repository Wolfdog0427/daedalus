/**
 * Daedalus Chat — Scoring-based Intent Classifier
 *
 * Replaces the old regex-first matcher with a multi-signal scorer:
 *   1. Exact phrase match (highest signal)
 *   2. Keyword token match
 *   3. Partial / substring overlap
 *   4. Context reinforcement from previous turn
 *
 * Returns { intent, confidence, topic } or { intent: "uncertain" }.
 */

import { INTENT_DEFS, type IntentDef } from "./IntentDefinitions";

export interface IntentResult {
  intent: string;
  confidence: number;
  topic: string;
}

const CONFIDENCE_THRESHOLD = 0.25;
const CONTEXT_BOOST = 0.15;
const PHRASE_SCORE = 3.0;
const KEYWORD_SCORE = 1.5;
const PARTIAL_SCORE = 0.4;

let _lastIntent: string | null = null;
let _lastTopic: string | null = null;
let _consecutiveUncertain = 0;

function normalize(input: string): string {
  return input.toLowerCase().replace(/[^a-z0-9\s'-]/g, "").replace(/\s+/g, " ").trim();
}

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

function scoreIntent(normalized: string, tokens: string[], def: IntentDef): number {
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

  if (def.name === _lastIntent && score > 0) {
    score += CONTEXT_BOOST;
  }

  score *= def.weight;

  return score;
}

/**
 * Classify an operator message into the best-matching intent.
 */
export function classifyIntent(input: string): IntentResult {
  const normalized = normalize(input);
  const tokens = tokenize(normalized);

  if (tokens.length === 0) {
    return { intent: "uncertain", confidence: 0, topic: "" };
  }

  let bestIntent = "";
  let bestScore = 0;

  for (const def of INTENT_DEFS) {
    const s = scoreIntent(normalized, tokens, def);
    if (s > bestScore) {
      bestScore = s;
      bestIntent = def.name;
    }
  }

  const maxPossible = Math.max(
    ...INTENT_DEFS.map(d => (d.phrases.length * PHRASE_SCORE + d.keywords.length * KEYWORD_SCORE) * d.weight)
  );
  const confidence = maxPossible > 0 ? Math.min(1, bestScore / Math.max(maxPossible * 0.25, 1)) : 0;

  if (bestScore < CONFIDENCE_THRESHOLD || !bestIntent) {
    _consecutiveUncertain++;
    return { intent: "uncertain", confidence, topic: normalized };
  }

  _consecutiveUncertain = 0;
  _lastIntent = bestIntent;
  _lastTopic = normalized;

  return { intent: bestIntent, confidence, topic: normalized };
}

// ── Context accessors ───────────────────────────────────────

export function getLastIntent(): string | null {
  return _lastIntent;
}

export function getLastTopic(): string | null {
  return _lastTopic;
}

export function getConsecutiveUncertain(): number {
  return _consecutiveUncertain;
}

export function resetContext(): void {
  _lastIntent = null;
  _lastTopic = null;
  _consecutiveUncertain = 0;
}
