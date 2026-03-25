/**
 * Daedalus Chat Service
 *
 * Core orchestrator for operator ↔ Daedalus conversation.
 *
 * - Accepts raw operator text + optional sessionId
 * - Normalises and classifies via scoring-based IntentClassifier
 * - Maintains per-session context (lastIntent, lastTopic)
 * - Routes to the correct compose handler
 * - Uses FallbackVariation when intent is "uncertain"
 * - Returns an enriched response shape with intent + confidence + context
 *
 * Does NOT modify any core Daedalus logic.
 */

import { strategyService } from "../strategy/StrategyService";
import { governanceService } from "../governance/GovernanceService";
import { getNodeMirrorRegistry } from "../mirror/NodeMirror";
import { getDaedalusEventBus, nowIso } from "../DaedalusEventBus";
import {
  classifyIntent,
  createContext,
  type IntentResult,
  type ChatContext,
} from "./IntentClassifier";
import { INTENT_DEFS } from "./IntentDefinitions";
import { getFallbackMessage, resetFallbackIndex } from "./FallbackVariation";

// ── Types ────────────────────────────────────────────────────────

export type ChatRole = "operator" | "daedalus" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  reply: string;
  intent: string;
  confidence: number;
  context: {
    lastIntent: string | null;
    lastTopic: string | null;
  };
}

export interface ChatHelpEntry {
  name: string;
  description: string;
  examples: string[];
}

// ── Session Context Store ────────────────────────────────────────

const DEFAULT_SESSION = "__default__";
const MAX_SESSIONS = 500;
const sessionContexts = new Map<string, ChatContext>();

function getOrCreateSession(sessionId: string | undefined | null): { id: string; ctx: ChatContext } {
  const id = (sessionId && sessionId.trim()) || DEFAULT_SESSION;
  let ctx = sessionContexts.get(id);
  if (!ctx) {
    if (sessionContexts.size >= MAX_SESSIONS) {
      const oldest = sessionContexts.keys().next().value;
      if (oldest) sessionContexts.delete(oldest);
    }
    ctx = createContext();
    sessionContexts.set(id, ctx);
  }
  return { id, ctx };
}

// ── Message History ──────────────────────────────────────────────

const MAX_HISTORY = 200;
let chatHistory: ChatMessage[] = [];
let messageCounter = 0;

function nextId(): string {
  return `msg-${++messageCounter}-${Date.now().toString(36)}`;
}

function pushMessage(role: ChatRole, content: string, context?: Record<string, unknown>): ChatMessage {
  const msg: ChatMessage = {
    id: nextId(),
    role,
    content,
    timestamp: new Date().toISOString(),
    context,
  };
  chatHistory.push(msg);
  if (chatHistory.length > MAX_HISTORY) {
    chatHistory = chatHistory.slice(-MAX_HISTORY);
  }
  return msg;
}

// ── System Snapshot ──────────────────────────────────────────────

type SystemSnapshot = ReturnType<typeof getSystemSnapshot>;

function getSystemSnapshot() {
  try {
    const evaluation = strategyService.getCachedEvaluation() ?? strategyService.evaluate();
    const tick = strategyService.getLastTickResult();
    const trust = strategyService.getOperatorTrustSnapshot();
    const regulation = strategyService.getLastRegulationOutput();
    const posture = governanceService.getPostureSnapshot();
    const registry = getNodeMirrorRegistry();
    const nodes = registry.toCockpitView();
    const freeze = strategyService.getConstitutionalFreezeState();
    const recentEvents = getDaedalusEventBus().getHistory(10);

    return {
      strategy: evaluation,
      escalation: tick?.escalation ?? null,
      safeMode: tick?.safeMode ?? null,
      drift: tick?.drift ?? null,
      operatorTrust: trust,
      regulation,
      posture: posture.posture,
      postureReason: posture.reason,
      nodeCount: nodes.length,
      quarantinedCount: nodes.filter(n => n.status === "quarantined").length,
      totalErrors: nodes.reduce((s, n) => s + n.errorCount, 0),
      freeze,
      recentEvents: recentEvents.map(e => ({ type: e.type, summary: e.summary })),
    };
  } catch {
    return null;
  }
}

// ── Acknowledgment Responses ────────────────────────────────────

function pickAck(input: string): string {
  const lower = input.toLowerCase();
  if (/\bthank/.test(lower)) return "Of course.";
  if (/\bok\b|\bokay\b|\balright\b/.test(lower)) return "Understood.";
  if (/\bgot it\b|\bunderstood\b/.test(lower)) return "Understood.";
  if (/\bperfect\b|\bgreat\b|\bgood\b|\bnice\b|\bawesome\b/.test(lower)) return "Glad that helps.";
  return "Noted.";
}

// ── Clarification Response ──────────────────────────────────────

const CLARIFICATION_MSG =
  "I can clarify. You can ask about status, trust, nodes, governance, incidents, or constitution. If you rephrase your last question, I'll try to be more precise.";

// ── Compose Responses ───────────────────────────────────────────

function compose(intent: string, snap: SystemSnapshot, expanded: boolean): string {
  if (!snap) return "I'm having trouble reading system state right now. The kernel may be initializing.";

  const { strategy, operatorTrust: trust, drift, safeMode, regulation, escalation, freeze } = snap;

  switch (intent) {
    case "greeting":
      return trust.boundOperatorId
        ? `Hello, ${trust.boundOperatorName ?? trust.boundOperatorId}. I'm here and monitoring. Alignment is at ${strategy.alignment}%, posture is ${trust.posture}. What do you need?`
        : "Hello. I'm Daedalus. No operator is currently bound — I'm running in unbound mode with high-risk actions disabled. You can bind an operator profile through the Operator Identity panel.";

    case "identity":
      if (expanded) {
        return [
          "I am Daedalus — a constitutional, distributed alignment organism.",
          "",
          "I maintain:",
          "  • Operator trust — multi-axis calibration of your identity",
          "  • Governance posture — constitutional oversight of all changes",
          "  • Strategy alignment — continuous evaluation across sovereignty, identity, governance, stability",
          "  • Fleet health — node heartbeats, capabilities, and quarantine",
          "  • Regulation loop — micro/macro corrections to prevent drift",
          "",
          "I operate under a constitutional framework with hard invariants that cannot be bypassed at runtime. My purpose is to serve and protect the operator's intent across any time horizon.",
        ].join("\n");
      }
      return "I am Daedalus — a constitutional, distributed alignment organism. I maintain operator trust, governance posture, strategy alignment, and fleet health. I operate under a constitutional framework with hard invariants that cannot be bypassed at runtime. My purpose is to serve and protect the operator's intent across any time horizon.";

    case "status": {
      const lines = [
        "Current state:",
        `  Strategy: ${strategy.name} (alignment ${strategy.alignment}%, confidence ${strategy.confidence}%)`,
        `  Operator: ${trust.boundOperatorId ? `${trust.boundOperatorName ?? trust.boundOperatorId} — ${trust.posture}, trust ${trust.trustScore}` : "unbound"}`,
        `  Governance: ${snap.posture}${snap.postureReason ? ` (${snap.postureReason})` : ""}`,
        `  Fleet: ${snap.nodeCount} nodes, ${snap.quarantinedCount} quarantined, ${snap.totalErrors} errors`,
      ];
      if (safeMode?.active) lines.push(`  ⚠ Safe mode is ACTIVE: ${safeMode.reason ?? "alignment critically low"}`);
      if (freeze.frozen) lines.push(`  🔒 Constitutional freeze: ${freeze.reason}`);
      if (drift?.drifting) lines.push(`  ↓ Alignment drift detected: ${drift.delta.toFixed(1)}pt`);
      lines.push(`\nAll systems are ${safeMode?.active ? "under safe mode governance" : "nominal"}.`);

      if (expanded) {
        lines.push("");
        lines.push("Detailed breakdown:");
        lines.push(`  Alignment axes: sovereignty ${strategy.alignmentBreakdown.sovereignty}%, identity ${strategy.alignmentBreakdown.identity}%, governance ${strategy.alignmentBreakdown.governance}%, stability ${strategy.alignmentBreakdown.stability}%`);
        lines.push(`  Trust axes: credentials ${trust.axes.credentials}, device ${trust.axes.deviceGraph}, behavior ${trust.axes.behaviorProfile}, continuity ${trust.axes.continuity}`);
        if (regulation) {
          const dm = regulation.driftMetrics ?? { magnitude: 0, slope: 0, acceleration: 0 };
          lines.push(`  Regulation: micro ${regulation.microAdjustment.toFixed(3)}, macro ${regulation.macroAdjustment.toFixed(3)}, drift magnitude ${dm.magnitude.toFixed(1)}`);
        }
      }
      return lines.join("\n");
    }

    case "strategy": {
      const lines = [
        `Strategy: ${strategy.name}`,
        `  Alignment: ${strategy.alignment}% (confidence ${strategy.confidence}%)`,
        `  Breakdown: sovereignty ${strategy.alignmentBreakdown.sovereignty}%, identity ${strategy.alignmentBreakdown.identity}%, governance ${strategy.alignmentBreakdown.governance}%, stability ${strategy.alignmentBreakdown.stability}%`,
        `  Weakest: ${strategy.weakestAxis} | Strongest: ${strategy.strongestAxis}`,
      ];
      if (strategy.notes) lines.push(`\n${strategy.notes}`);
      if (expanded) {
        lines.push("");
        lines.push("The alignment pipeline evaluates strategy on every kernel tick. Self-correction adjusts sensitivity and strictness when alignment trends below the floor. The escalation module pauses autonomy below 50%.");
      }
      return lines.filter(Boolean).join("\n");
    }

    case "trust":
      if (!trust.boundOperatorId)
        return "No operator is bound. I'm in unbound mode — all high-risk actions are disabled until an operator binds through the Operator Identity panel.";
      {
        const lines = [
          `Operator: ${trust.boundOperatorName ?? trust.boundOperatorId}`,
          `  Posture: ${trust.posture} | Comfort: ${trust.comfortPosture}`,
          `  Trust score: ${trust.trustScore}`,
          `  Axes: credentials ${trust.axes.credentials}, device ${trust.axes.deviceGraph}, behavior ${trust.axes.behaviorProfile}, continuity ${trust.axes.continuity}`,
          `  Calibrated: ${trust.calibrated ? "yes" : "not yet"}`,
          `\n${trust.narrative}`,
        ];
        if (expanded) {
          lines.push("");
          lines.push("Trust rises slowly through consistent behavior and falls quickly on anomalies. High-risk actions (governance, invariant edits, node authority) are only allowed when trust exceeds the high-risk threshold and all axes are above their minimums.");
        }
        return lines.join("\n");
      }

    case "nodes": {
      const lines = [
        `Fleet: ${snap.nodeCount} nodes`,
        `  Quarantined: ${snap.quarantinedCount}`,
        `  Total errors: ${snap.totalErrors}`,
        snap.quarantinedCount > 0
          ? "\nSome nodes are quarantined. Check the Node Cortex panel for details and consider investigating or detaching problem nodes."
          : "\nFleet is healthy. No quarantined nodes.",
      ];
      if (expanded) {
        lines.push("");
        lines.push("The node fabric continuously heartbeats each node, tracks capabilities, and quarantines nodes that exceed error thresholds or fail liveness checks.");
      }
      return lines.join("\n");
    }

    case "safemode":
      if (safeMode?.active)
        return `Safe mode is ACTIVE. Reason: ${safeMode.reason ?? "alignment critically low"}. Autonomy is reduced and caution is elevated. The system will exit safe mode when alignment recovers above the floor.`;
      if (freeze.frozen)
        return `Constitutional freeze is active: ${freeze.reason}. During freeze, no governance changes are allowed. Disable the freeze from the Operator Identity panel when ready.`;
      return "Neither safe mode nor constitutional freeze is active. The system is operating normally.";

    case "regulation": {
      if (!regulation)
        return "The regulation loop hasn't produced output yet. It runs on each kernel tick to apply micro and macro corrections to alignment.";
      const dm = regulation.driftMetrics ?? { magnitude: 0, slope: 0, acceleration: 0 };
      const tel = regulation.telemetry ?? { appliedMacro: false, reason: "none" };
      const lines = [
        "Regulation loop:",
        `  Micro-adjustment: ${regulation.microAdjustment.toFixed(3)}`,
        `  Macro-adjustment: ${regulation.macroAdjustment.toFixed(3)}`,
        `  Drift: magnitude ${dm.magnitude.toFixed(1)}, slope ${dm.slope.toFixed(3)}, acceleration ${dm.acceleration.toFixed(3)}`,
        tel.appliedMacro ? `  Macro-correction fired: ${tel.reason}` : "  Macro-correction: not needed",
      ];
      if (regulation.shouldEnterSafeMode) lines.push("  Recommending safe mode entry");
      if (regulation.shouldPauseAutonomy) lines.push("  Recommending autonomy pause");
      if (expanded) {
        lines.push("");
        lines.push("Micro-corrections run continuously to gently nudge alignment toward target. Macro-corrections fire under severe or accelerating drift, damped to avoid overshoot.");
      }
      return lines.join("\n");
    }

    case "governance": {
      const lines = [`Governance posture: ${snap.posture}`];
      if (snap.postureReason) lines.push(`  Reason: ${snap.postureReason}`);
      lines.push("\nYou can manage overrides, drifts, and votes from the governance section of the Orchestrator panel.");
      if (expanded) {
        lines.push("");
        lines.push("The governance engine holds constitutional authority over all changes. Overrides, votes, and posture shifts are all logged to the governance ledger.");
      }
      return lines.join("\n");
    }

    case "escalation":
      if (!escalation || escalation.level === "none")
        return "No escalation active. Alignment is within acceptable bounds.";
      return `Escalation level: ${escalation.level.toUpperCase()}${escalation.reason ? ` — ${escalation.reason}` : ""}. ${escalation.level === "critical" ? "Autonomy is paused. Operator intervention may be needed." : "Monitoring closely."}`;

    case "incidents":
      return snap.totalErrors > 0
        ? `There are ${snap.totalErrors} total errors across the fleet and ${snap.quarantinedCount} quarantined nodes. Check the Incidents panel to open, track, and resolve issues.`
        : "No errors or incidents detected across the fleet. Everything is clean.";

    case "help":
      return [
        "You can ask me about:",
        "  • status — overall system state",
        "  • strategy / alignment — current strategy and alignment breakdown",
        "  • trust / operator — operator identity and trust posture",
        "  • nodes / fleet — node health and fleet status",
        "  • safe mode / freeze — constitutional safety state",
        "  • regulation / drift — alignment regulation loop",
        "  • governance / posture — governance state",
        "  • escalation — current escalation level",
        "  • incidents / errors — fleet issues",
        "  • approval / gate — auto-approval gate state",
        "  • rollback / registry — tracked change registry",
        "  • history / events — recent event log",
        "  • constitution — being constitution status",
        "\nOr just talk to me naturally — I understand a wide range of phrasings.",
      ].join("\n");

    case "history": {
      if (snap.recentEvents.length === 0) return "No recent events in the event bus.";
      const lines = ["Recent events:"];
      for (const e of snap.recentEvents.slice(0, 8)) {
        lines.push(`  [${e.type}] ${e.summary ?? ""}`);
      }
      if (expanded && snap.recentEvents.length > 8) {
        for (const e of snap.recentEvents.slice(8)) {
          lines.push(`  [${e.type}] ${e.summary ?? ""}`);
        }
      }
      return lines.join("\n");
    }

    case "constitution":
      if (expanded) {
        return [
          "The being constitution validates all being presences against invariant checks:",
          "  • Valid posture",
          "  • Presence mode",
          "  • Attention level",
          "  • Bounded influence",
          "  • Continuity coherence",
          "  • Anchor existence",
          "  • Operator presence",
          "\nCheck the Constitution panel for the full report.",
        ].join("\n");
      }
      return "The being constitution validates all being presences against invariant checks — valid posture, presence mode, attention level, bounded influence, continuity coherence, anchor existence, and operator presence. Check the Constitution panel for the full report.";

    case "approval": {
      const gate = strategyService.getApprovalGateConfig();
      return [
        "Auto-approval gate:",
        `  Alignment threshold: ${gate.alignmentThreshold}%`,
        `  Confidence threshold: ${gate.confidenceThreshold}%`,
        `  Cooldown: ${gate.cooldownMs}ms`,
        `  Allow during safe mode: ${gate.allowDuringSafeMode ? "yes" : "no"}`,
        "\nChanges meeting all thresholds are auto-approved. Others require operator review.",
      ].join("\n");
    }

    case "rollback": {
      const snap2 = strategyService.getRollbackRegistrySnapshot();
      return [
        "Rollback registry:",
        `  Active tracked changes: ${snap2.activeChanges.length}`,
        `  Accepted: ${snap2.acceptedCount}`,
        `  Rolled back: ${snap2.rolledBackCount}`,
        snap2.recentRollbacks.length > 0
          ? `  Recent rollbacks: ${snap2.recentRollbacks.map(r => r.changeId).join(", ")}`
          : "  No recent rollbacks.",
      ].join("\n");
    }

    default:
      return getFallbackMessage();
  }
}

// ── Route Intent to Response ────────────────────────────────────

function routeIntent(
  result: IntentResult,
  ctx: ChatContext,
  snap: SystemSnapshot,
  rawInput: string,
): { reply: string; resolvedIntent: string } {
  const intent = result.intent;

  if (intent === "acknowledgment") {
    return { reply: pickAck(rawInput), resolvedIntent: "acknowledgment" };
  }

  if (intent === "followup") {
    if (ctx.lastIntent && ctx.lastIntent !== "followup" && ctx.lastIntent !== "acknowledgment" && ctx.lastIntent !== "uncertain") {
      return { reply: compose(ctx.lastIntent, snap, true), resolvedIntent: ctx.lastIntent };
    }
    return {
      reply: "I'd be happy to elaborate, but I'm not sure what we were discussing. What would you like to know about?",
      resolvedIntent: "uncertain",
    };
  }

  if (intent === "clarification") {
    if (ctx.lastIntent && ctx.lastIntent !== "clarification" && ctx.lastIntent !== "uncertain") {
      return { reply: compose(ctx.lastIntent, snap, true), resolvedIntent: ctx.lastIntent };
    }
    return { reply: CLARIFICATION_MSG, resolvedIntent: "clarification" };
  }

  if (intent === "uncertain") {
    return { reply: getFallbackMessage(), resolvedIntent: "uncertain" };
  }

  return { reply: compose(intent, snap, false), resolvedIntent: intent };
}

// ── Public API ──────────────────────────────────────────────────

/**
 * Process an operator message with optional session isolation.
 * Returns both the legacy ChatMessage pair AND the enriched ChatResponse.
 */
export function processMessage(
  content: string,
  sessionId?: string,
): {
  userMessage: ChatMessage;
  daedalusMessage: ChatMessage;
  response: ChatResponse;
} {
  const { ctx } = getOrCreateSession(sessionId);
  const userMessage = pushMessage("operator", content);

  const result = classifyIntent(content, ctx);
  const snap = getSystemSnapshot();
  const { reply, resolvedIntent } = routeIntent(result, ctx, snap, content);

  if (resolvedIntent !== "uncertain") {
    ctx.lastIntent = resolvedIntent;
    ctx.lastTopic = result.topic || null;
  }

  const daedalusMessage = pushMessage("daedalus", reply, {
    intent: resolvedIntent,
    confidence: result.confidence,
    topic: result.topic,
    strategy: snap?.strategy.name,
    alignment: snap?.strategy.alignment,
  });

  getDaedalusEventBus().publish({
    type: "OPERATOR_CHAT_MESSAGE",
    timestamp: nowIso(),
    summary: `Operator: "${content.slice(0, 80)}${content.length > 80 ? "..." : ""}"`,
  });

  const response: ChatResponse = {
    reply,
    intent: resolvedIntent,
    confidence: result.confidence,
    context: {
      lastIntent: ctx.lastIntent,
      lastTopic: ctx.lastTopic,
    },
  };

  return { userMessage, daedalusMessage, response };
}

export function getChatHistory(limit = 100): ChatMessage[] {
  return chatHistory.slice(-limit);
}

export function clearChatHistory(sessionId?: string): void {
  chatHistory = [];
  if (sessionId) {
    sessionContexts.delete(sessionId);
  } else {
    sessionContexts.clear();
  }
  resetFallbackIndex();
}

export function getWelcomeMessage(): ChatMessage {
  if (chatHistory.length > 0) return chatHistory[0];
  return pushMessage("daedalus", "I am Daedalus. Ask me anything about the system — status, strategy, trust, nodes, governance, or say \"help\" to see what I can answer.");
}

/**
 * Static help data for GET /daedalus/chat/help
 */
export function getChatHelp(): { intents: ChatHelpEntry[] } {
  const visible = INTENT_DEFS.filter(d =>
    !["greeting", "acknowledgment", "followup", "clarification"].includes(d.name)
  );
  return {
    intents: visible.map(d => ({
      name: d.name,
      description: d.description,
      examples: d.examples,
    })),
  };
}

/**
 * Get or peek at a session's context (for testing / debugging).
 */
export function getSessionContext(sessionId?: string): ChatContext | null {
  const id = (sessionId && sessionId.trim()) || DEFAULT_SESSION;
  return sessionContexts.get(id) ?? null;
}
