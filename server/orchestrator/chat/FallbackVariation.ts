/**
 * Daedalus Chat — Fallback Variation Generator
 *
 * Provides rotating, non-repetitive fallback messages when the intent
 * classifier cannot determine what the operator meant.  A simple
 * in-memory index ensures consecutive uncertain responses never repeat
 * the same text.
 */

const fallbackTemplates = [
  "I'm not entirely sure what you meant. Here are a few things I can help with: status, trust, nodes, governance, incidents, or constitution.",
  "I may need a bit more clarity. You can ask about system status, trust posture, node health, governance, or say 'help' for the full list.",
  "I didn't fully catch that. Try asking about status, nodes, trust, governance, or use 'help' to see everything I can do.",
  "Not completely sure what you meant. If you're looking for something specific, you can ask about status, trust, nodes, incidents, or governance.",
  "I might need a clearer phrasing. Common topics are: status, trust, nodes, governance, incidents. You can also say 'help' for more options.",
];

let fallbackIndex = 0;

export function getFallbackMessage(): string {
  const msg = fallbackTemplates[fallbackIndex];
  fallbackIndex = (fallbackIndex + 1) % fallbackTemplates.length;
  return msg;
}

export function resetFallbackIndex(): void {
  fallbackIndex = 0;
}
