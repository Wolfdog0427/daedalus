import { useState } from "react";
import type { GovernorDisplayInfo, GovernorPresetName } from "../shared/daedalus/governor";
import type { TimelineSnapshot } from "../shared/daedalus/timeline";
import type { GrammarResult } from "../shared/daedalus/sceneGrammar";
import type { OrchestratedScene } from "../shared/daedalus/sceneOrchestration";
import type { OperatorAffectState } from "../shared/daedalus/operatorAffect";
import type { DaedalusPosture } from "../shared/daedalus/contracts";
import type { PersistenceInfo } from "../hooks/useScenePersistence";
import type { TelemetryEvent } from "../shared/daedalus/sceneTelemetry";
import { summarizePayload } from "../shared/daedalus/sceneTelemetryEngine";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { AdaptationSnapshot } from "../shared/daedalus/sceneAdaptation";
import type { AutonomyState } from "../hooks/useSceneAutonomy";
import type { IntentModelState } from "../hooks/useIntentModel";
import type { StrategyModelState } from "../hooks/useExpressiveStrategy";
import type { MetaStrategyModelState } from "../hooks/useMetaStrategy";
import type { MetaGovernanceModelState } from "../hooks/useMetaGovernance";
import type { FabricDashboard } from "../shared/daedalus/governanceFabric";
import type { KernelHaloSnapshot } from "../shared/daedalus/kernelHalo";
import type { CrownState } from "../shared/daedalus/kernelCrown";
import type { ExpressiveState, SubPosture as SubPostureType, ExpressiveOverlayType } from "../api/daedalusClient";
import { sendOperatorCue, clearOperatorCue, setDaedalusContext } from "../api/daedalusClient";
import "./ExpressiveHud.css";

export const EXPRESSIVE_HUD_ENABLED = true;

const POSTURE_OPTIONS: DaedalusPosture[] = ["companion", "sentinel", "observer", "dormant"];
const PRESET_OPTIONS: GovernorPresetName[] = ["default", "calm", "responsive"];

const POSTURE_DESCRIPTIONS: Record<DaedalusPosture, string> = {
  companion: "Friendly, conversational",
  sentinel: "Watchful, protective",
  observer: "Quiet, monitoring",
  dormant: "Minimal activity",
};

const PRESET_DESCRIPTIONS: Record<GovernorPresetName, string> = {
  default: "Balanced behavior",
  calm: "Slower, smoother transitions",
  responsive: "Faster, more reactive",
};

interface Props {
  scene: OrchestratedScene;
  grammar: GrammarResult;
  frameId: number;
  persistence: PersistenceInfo;
  telemetry: TelemetryEvent[];
  analytics: AnalyticsSnapshot;
  adaptation: AdaptationSnapshot;
  autonomy: AutonomyState;
  intent: IntentModelState;
  strategy: StrategyModelState;
  metaStrategy: MetaStrategyModelState;
  metaGov: MetaGovernanceModelState;
  fabricDashboard: FabricDashboard;
  fabricClearAll: () => void;
  halo: KernelHaloSnapshot;
  crown: CrownState;
  kernelRollback: () => void;
  governorDisplay: GovernorDisplayInfo;
  timeline: TimelineSnapshot;
  affect: OperatorAffectState;
  governorPreset: GovernorPresetName;
  postureNudge: DaedalusPosture | null;
  onToggleGovernor: () => void;
  onSetPreset: (preset: GovernorPresetName) => void;
  onNudgePosture: (posture: DaedalusPosture | null) => void;
  expressiveState: ExpressiveState | null;
}

function formatAge(ms: number): string {
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m`;
  return `${(ms / 3_600_000).toFixed(1)}h`;
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

type HealthLevel = "good" | "ok" | "warn" | "critical";

function healthLevel(v: number, inverted = false): HealthLevel {
  const val = inverted ? 1 - v : v;
  if (val >= 0.85) return "good";
  if (val >= 0.65) return "ok";
  if (val >= 0.4) return "warn";
  return "critical";
}

function healthColor(level: HealthLevel): string {
  switch (level) {
    case "good": return "#3fb950";
    case "ok": return "#58a6ff";
    case "warn": return "#d29922";
    case "critical": return "#f85149";
  }
}

function HealthBar({ value, label, description, inverted = false }: { value: number; label: string; description?: string; inverted?: boolean }) {
  const level = healthLevel(value, inverted);
  const color = healthColor(level);
  return (
    <div className="xhud-bar-row" title={description}>
      <span className="xhud-bar-label">{label}</span>
      <div className="xhud-bar-track">
        <div className="xhud-bar-fill" style={{ width: `${value * 100}%`, background: color }} />
      </div>
      <span className="xhud-bar-value" style={{ color }}>{pct(value)}</span>
    </div>
  );
}

function StatusDot({ level }: { level: HealthLevel }) {
  return <span className={`xhud-dot xhud-dot--${level}`} />;
}

function SectionHeader({ title, subtitle, open, onToggle }: { title: string; subtitle?: string; open?: boolean; onToggle?: () => void }) {
  const interactive = onToggle != null;
  return (
    <div
      className={`xhud-section-header ${interactive ? "xhud-section-header--clickable" : ""}`}
      onClick={onToggle}
    >
      <div className="xhud-section-header__text">
        <span className="xhud-section-header__title">{title}</span>
        {subtitle && <span className="xhud-section-header__subtitle">{subtitle}</span>}
      </div>
      {interactive && <span className="xhud-section-header__chevron">{open ? "▾" : "▸"}</span>}
    </div>
  );
}

function ProposalCard({ label, color, reason, time, onApprove, onReject }: {
  label: string; color: string; reason: string; time: number;
  onApprove: () => void; onReject: () => void;
}) {
  return (
    <div className="xhud-proposal" style={{ borderColor: color + "40" }}>
      <div className="xhud-proposal__header">
        <span className="xhud-proposal__label" style={{ color, borderColor: color + "40", background: color + "14" }}>{label}</span>
        <span className="xhud-proposal__time">{formatTime(time)}</span>
      </div>
      <p className="xhud-proposal__reason">{reason}</p>
      <div className="xhud-proposal__actions">
        <button className="xhud-btn xhud-btn--approve" onClick={onApprove}>Approve</button>
        <button className="xhud-btn xhud-btn--reject" onClick={onReject}>Reject</button>
      </div>
    </div>
  );
}

const TELEMETRY_VISIBLE_COUNT = 8;

const SUB_POSTURE_LABELS: Record<string, { label: string; color: string }> = {
  none: { label: "Neutral", color: "#8b949e" },
  analytic: { label: "Analytic", color: "#58a6ff" },
  creative: { label: "Creative", color: "#a371f7" },
  sensitive: { label: "Sensitive", color: "#f778ba" },
  defensive: { label: "Defensive", color: "#f85149" },
  supportive: { label: "Supportive", color: "#3fb950" },
};

const OVERLAY_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  none: { label: "None", color: "#8b949e", icon: "—" },
  focus: { label: "Focus", color: "#58a6ff", icon: "◎" },
  calm: { label: "Calm", color: "#3fb950", icon: "◌" },
  alert: { label: "Alert", color: "#f85149", icon: "⚠" },
  recovery: { label: "Recovery", color: "#d29922", icon: "↻" },
  transition: { label: "Transition", color: "#a371f7", icon: "⇄" },
};

const SUB_POSTURE_OPTIONS = ["none", "analytic", "creative", "sensitive", "defensive", "supportive"] as const;
const OVERLAY_OPTIONS = ["none", "focus", "calm", "alert", "recovery", "transition"] as const;
const TASK_OPTIONS = ["idle", "analysis", "creative", "review", "sensitive"] as const;
const ENV_OPTIONS = ["normal", "crisis", "handoff", "recovery"] as const;

export function ExpressiveHud({
  scene, grammar, frameId, persistence, telemetry, analytics, adaptation,
  autonomy, intent, strategy, metaStrategy, metaGov, fabricDashboard,
  fabricClearAll, halo, crown, kernelRollback, governorDisplay, timeline,
  affect, governorPreset, postureNudge, onToggleGovernor, onSetPreset, onNudgePosture,
  expressiveState,
}: Props) {
  const [hudCollapsed, setHudCollapsed] = useState(true);
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [adaptationOpen, setAdaptationOpen] = useState(false);
  const [layersOpen, setLayersOpen] = useState(false);
  const [expressiveOpen, setExpressiveOpen] = useState(false);
  const [cueOpen, setCueOpen] = useState(false);

  if (!EXPRESSIVE_HUD_ENABLED) return null;

  const visibleEvents = telemetry.slice(-TELEMETRY_VISIBLE_COUNT).reverse();

  const overallHealth = analytics.expressiveHealth;
  const overallLevel = healthLevel(overallHealth);
  const statusWord = overallLevel === "good" ? "Healthy" : overallLevel === "ok" ? "Stable" : overallLevel === "warn" ? "Degraded" : "Critical";

  const hasPendingProposal = !!(autonomy.pending || intent.pending || strategy.pending || metaStrategy.pending || metaGov.pending);
  const pendingProposalCount = [autonomy.pending, intent.pending, strategy.pending, metaStrategy.pending, metaGov.pending].filter(Boolean).length;

  return (
    <div className={`expressive-hud cin-arrive${hudCollapsed ? " expressive-hud--collapsed" : ""}`}>
      {/* ── Collapsed / Title Bar ──────────────────────────────────── */}
      <div className="xhud-titlebar" onClick={() => setHudCollapsed(v => !v)}>
        <div className="xhud-titlebar__left">
          <StatusDot level={overallLevel} />
          <span className="xhud-titlebar__name">Daedalus</span>
          <span className={`xhud-titlebar__status xhud-titlebar__status--${overallLevel}`}>{statusWord}</span>
        </div>
        <div className="xhud-titlebar__right">
          {hasPendingProposal && (
            <span className="xhud-titlebar__pending">{pendingProposalCount} pending</span>
          )}
          <span className="xhud-titlebar__toggle">{hudCollapsed ? "▸" : "▾"}</span>
        </div>
      </div>

      {/* ── Collapsed summary row ──────────────────────────────────── */}
      {hudCollapsed && (
        <div className="xhud-collapsed-summary">
          <span className={`xhud-mini-tag xhud-posture--${scene.posture}`}>{scene.posture}</span>
          <span className="xhud-mini-tag">{scene.sceneName}</span>
          {expressiveState && expressiveState.subPosture !== "none" && (
            <span className="xhud-mini-tag" style={{ color: SUB_POSTURE_LABELS[expressiveState.subPosture]?.color, borderColor: SUB_POSTURE_LABELS[expressiveState.subPosture]?.color + "40" }}>
              {SUB_POSTURE_LABELS[expressiveState.subPosture]?.label}
            </span>
          )}
          {expressiveState && expressiveState.overlay !== "none" && (
            <span className="xhud-mini-tag" style={{ color: OVERLAY_LABELS[expressiveState.overlay]?.color }}>
              {OVERLAY_LABELS[expressiveState.overlay]?.icon}
            </span>
          )}
          <span className="xhud-collapsed-health" style={{ color: healthColor(overallLevel) }}>{pct(overallHealth)}</span>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          EXPANDED CONTENT
          ════════════════════════════════════════════════════════════ */}

      {/* ── 1. Organism Status Summary ─────────────────────────────── */}
      <div className="xhud-summary">
        <div className="xhud-summary__row">
          <span className="xhud-summary__crown" title={`Crown: ${crown.symbol} — stability ${pct(crown.stability)}`}
            style={{ opacity: 0.5 + crown.glow * 0.5 }}>{crown.symbol}</span>
          <span className="xhud-summary__scene">
            Scene: <strong className={`xhud-scene--${scene.sceneName}`}>{scene.sceneName}</strong>
          </span>
          <span className="xhud-summary__frame">Frame {frameId}</span>
        </div>

        {scene.narrativeLine && (
          <p className={`xhud-narrative xhud-narrative--${scene.tone}`}>{scene.narrativeLine}</p>
        )}
      </div>

      {/* ── 2. Kernel Health ───────────────────────────────────────── */}
      <div className={`xhud-kernel xhud-kernel--${halo.kernelStatus}`}>
        <div className="xhud-kernel__top">
          <span className="xhud-kernel__label">Kernel</span>
          <span className={`xhud-kernel__status xhud-kernel-status--${halo.kernelStatus}`}>{halo.kernelStatus}</span>
          <span className={`xhud-kernel__shell xhud-shell--${halo.shellStatus}`}>{halo.shellStatus === "nominal" ? "Shell OK" : "Shell Degraded"}</span>
          <span className={`xhud-kernel__inv ${halo.invariantsPassed ? "xhud-inv--ok" : "xhud-inv--fail"}`}
            title={halo.invariantsPassed ? "All invariants pass" : `Failed: ${halo.failedInvariants.join(", ")}`}>
            Invariants: {halo.invariantsHeld}/{halo.invariantsTotal}
          </span>
        </div>
        {(halo.overrideCount > 0 || halo.pendingCount > 0 || halo.kernelStatus !== "clean") && (
          <div className="xhud-kernel__detail">
            {halo.overrideCount > 0 && <span className="xhud-mini-tag xhud-mini-tag--muted">{halo.overrideCount} override{halo.overrideCount !== 1 ? "s" : ""}</span>}
            {halo.pendingCount > 0 && <span className="xhud-mini-tag xhud-mini-tag--purple">{halo.pendingCount} pending</span>}
            {halo.kernelStatus !== "clean" && (
              <button className="xhud-btn xhud-btn--danger-sm" onClick={kernelRollback}>Rollback Kernel</button>
            )}
          </div>
        )}
      </div>

      {/* ── 3. Organism State ──────────────────────────────────────── */}
      <SectionHeader title="Organism State" subtitle="Current posture, mood, and expression" />
      <div className="xhud-state-grid">
        <div className="xhud-state-cell">
          <span className="xhud-state-label">Posture</span>
          <span className={`xhud-state-value xhud-posture--${scene.posture}`}>{scene.posture}</span>
        </div>
        <div className="xhud-state-cell">
          <span className="xhud-state-label">Affect</span>
          <span className="xhud-state-value">{affect}</span>
        </div>
        <div className="xhud-state-cell">
          <span className="xhud-state-label">Mode</span>
          <span className={`xhud-state-value xhud-mode--${scene.mode}`}>{scene.mode}</span>
        </div>
        <div className="xhud-state-cell">
          <span className="xhud-state-label">Tone</span>
          <span className={`xhud-state-value xhud-tone--${scene.tone}`}>{scene.tone}</span>
        </div>
      </div>

      {scene.continuityBadge && (
        <div className="xhud-badge">
          <span className="xhud-badge__label">Continuity</span>
          <span className="xhud-badge__value">{scene.continuityBadge.label}</span>
        </div>
      )}

      {/* ── 4. Vitals ─────────────────────────────────────────────── */}
      <SectionHeader title="Vitals" subtitle="Expressive health and stability metrics" />
      <div className="xhud-vitals">
        <HealthBar value={scene.glow} label="Glow" description="Expressive energy level — higher means more active expression" />
        <HealthBar value={scene.motion} label="Motion" description="Scene transition activity — higher means more dynamic" />
        <HealthBar value={analytics.expressiveHealth} label="Health" description="Overall expressive system health" />
        <HealthBar value={analytics.sceneStability} label="Stability" description="How stable the current scene is — higher is calmer" />
        <HealthBar value={analytics.momentumVolatility} label="Volatility" description="How erratic momentum changes are — lower is better" inverted />
      </div>

      {/* ── 4b. Expressive Physiology ──────────────────────────────── */}
      <SectionHeader title="Expressive Physiology" subtitle="Sub-posture, overlay, micro-posture, and context"
        open={expressiveOpen} onToggle={() => setExpressiveOpen(v => !v)} />

      {expressiveOpen && expressiveState && (
        <div className="xhud-expressive">
          <div className="xhud-state-grid">
            <div className="xhud-state-cell">
              <span className="xhud-state-label">Sub-Posture</span>
              <span className="xhud-state-value" style={{ color: SUB_POSTURE_LABELS[expressiveState.subPosture]?.color }}>
                {SUB_POSTURE_LABELS[expressiveState.subPosture]?.label ?? expressiveState.subPosture}
              </span>
            </div>
            <div className="xhud-state-cell">
              <span className="xhud-state-label">Overlay</span>
              <span className="xhud-state-value" style={{ color: OVERLAY_LABELS[expressiveState.overlay]?.color }}>
                {OVERLAY_LABELS[expressiveState.overlay]?.icon}{" "}
                {OVERLAY_LABELS[expressiveState.overlay]?.label ?? expressiveState.overlay}
                {expressiveState.overlayTicksRemaining > 0 && (
                  <span className="xhud-mini-tag xhud-mini-tag--muted" style={{ marginLeft: 4 }}>
                    {expressiveState.overlayTicksRemaining}t
                  </span>
                )}
              </span>
            </div>
            <div className="xhud-state-cell">
              <span className="xhud-state-label">Context</span>
              <span className="xhud-state-value">{expressiveState.contextual.reason}</span>
            </div>
          </div>

          <div className="xhud-vitals" style={{ marginTop: 8 }}>
            <HealthBar value={expressiveState.microPosture.responsiveness} label="μ Responsiveness" description="Micro-posture responsiveness — alignment-driven" />
            <HealthBar value={1 - expressiveState.microPosture.caution} label="μ Ease" description="Inverse of micro-caution — higher means less caution" />
            <HealthBar value={expressiveState.microPosture.expressiveness} label="μ Expressiveness" description="Micro-posture expressiveness — confidence-driven" />
          </div>

          <SectionHeader title="Operator Cue" subtitle="Send a posture hint to Daedalus"
            open={cueOpen} onToggle={() => setCueOpen(v => !v)} />

          {cueOpen && (
            <div className="xhud-cue-controls">
              <div className="xhud-control-group">
                <span className="xhud-control-label">Sub-Posture Override</span>
                <div className="xhud-control-options">
                  {SUB_POSTURE_OPTIONS.map(sp => (
                    <button key={sp} className="xhud-btn xhud-btn--option"
                      style={{ borderColor: SUB_POSTURE_LABELS[sp]?.color + "60", color: SUB_POSTURE_LABELS[sp]?.color }}
                      onClick={() => { sendOperatorCue({ subPostureBias: sp as SubPostureType }).catch(() => {}); }}>
                      {SUB_POSTURE_LABELS[sp]?.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="xhud-control-group">
                <span className="xhud-control-label">Overlay Override</span>
                <div className="xhud-control-options">
                  {OVERLAY_OPTIONS.map(ov => (
                    <button key={ov} className="xhud-btn xhud-btn--option"
                      style={{ borderColor: OVERLAY_LABELS[ov]?.color + "60", color: OVERLAY_LABELS[ov]?.color }}
                      onClick={() => { sendOperatorCue({ overlayBias: ov as ExpressiveOverlayType }).catch(() => {}); }}>
                      {OVERLAY_LABELS[ov]?.icon} {OVERLAY_LABELS[ov]?.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="xhud-control-group">
                <span className="xhud-control-label">Task Context</span>
                <div className="xhud-control-options">
                  {TASK_OPTIONS.map(t => (
                    <button key={t} className="xhud-btn xhud-btn--option" onClick={() => { setDaedalusContext({ taskType: t }).catch(() => {}); }}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div className="xhud-control-group">
                <span className="xhud-control-label">Environment</span>
                <div className="xhud-control-options">
                  {ENV_OPTIONS.map(e => (
                    <button key={e} className="xhud-btn xhud-btn--option" onClick={() => { setDaedalusContext({ environment: e }).catch(() => {}); }}>
                      {e}
                    </button>
                  ))}
                </div>
              </div>
              <button className="xhud-btn xhud-btn--danger-full" onClick={() => { clearOperatorCue().catch(() => {}); }}>Clear Cue</button>
            </div>
          )}
        </div>
      )}

      {expressiveOpen && !expressiveState && (
        <div className="xhud-empty">No expressive data available yet</div>
      )}

      {/* ── 5. Timeline ───────────────────────────────────────────── */}
      <div className="xhud-timeline">
        <span className="xhud-timeline__label">Timeline</span>
        <span className={`xhud-timeline__phase xhud-phase--${timeline.phase}`}>{timeline.phase}</span>
        <div className="xhud-bar-track xhud-bar-track--sm">
          <div className="xhud-bar-fill" style={{ width: `${timeline.momentum * 100}%`, background: "rgba(210,153,34,0.6)" }} />
        </div>
        <span className="xhud-timeline__momentum">Momentum: {pct(timeline.momentum)}</span>
        <span className="xhud-timeline__events">{timeline.eventCount} events</span>
      </div>

      {grammar.blendMs > 0 || grammar.narrativeSync || !grammar.allowed || scene.progress < 1 ? (
        <div className="xhud-grammar">
          {grammar.blendMs > 0 && <span className="xhud-mini-tag xhud-mini-tag--blue">Blending {grammar.blendMs}ms</span>}
          {grammar.narrativeSync && <span className="xhud-mini-tag xhud-mini-tag--yellow">Narrative sync</span>}
          {!grammar.allowed && <span className="xhud-mini-tag xhud-mini-tag--red">Transition held</span>}
          {scene.progress < 1 && <span className="xhud-mini-tag xhud-mini-tag--muted">Progress: {Math.round(scene.progress * 100)}%</span>}
        </div>
      ) : null}

      {/* ── 6. Governor ───────────────────────────────────────────── */}
      <div className="xhud-governor">
        <span className="xhud-governor__label">Governor</span>
        <span className={`xhud-governor__status ${governorDisplay.enabled ? "xhud-gov--on" : "xhud-gov--off"}`}>
          {governorDisplay.enabled ? "Active" : "Disabled"}
        </span>
        {governorDisplay.escalationLocked && <span className="xhud-mini-tag xhud-mini-tag--red">Locked</span>}
        {governorDisplay.modeCooldownActive && <span className="xhud-mini-tag xhud-mini-tag--yellow">Mode cooldown</span>}
        {governorDisplay.toneCooldownActive && <span className="xhud-mini-tag xhud-mini-tag--yellow">Tone cooldown</span>}
      </div>

      {persistence.restoredFrom && (
        <div className="xhud-persistence">
          <span className="xhud-mini-tag xhud-mini-tag--purple">Restored</span>
          <span className="xhud-persistence__from">{persistence.restoredFrom.sceneName}</span>
          <span className="xhud-persistence__age">{formatAge(persistence.ageMs!)}</span>
        </div>
      )}

      {/* ── 7. Pending Proposals ──────────────────────────────────── */}
      {hasPendingProposal && (
        <>
          <SectionHeader title="Pending Proposals" subtitle="Daedalus is requesting your approval for these changes" />
          {autonomy.pending && (
            <ProposalCard label="Autonomy" color="#d29922" reason={autonomy.pending.reason}
              time={autonomy.pending.timestamp} onApprove={() => autonomy.approve(autonomy.pending!.id)}
              onReject={() => autonomy.reject(autonomy.pending!.id)} />
          )}
          {intent.pending && (
            <ProposalCard label="Intent" color="#a371f7" reason={intent.pending.reason}
              time={intent.pending.timestamp} onApprove={() => intent.approve(intent.pending!.id)}
              onReject={() => intent.reject(intent.pending!.id)} />
          )}
          {strategy.pending && (
            <ProposalCard label="Strategy" color="#56d4cf" reason={strategy.pending.reason}
              time={strategy.pending.timestamp} onApprove={() => strategy.approve(strategy.pending!.id)}
              onReject={() => strategy.reject(strategy.pending!.id)} />
          )}
          {metaStrategy.pending && (
            <ProposalCard label="Meta-Strategy" color="#db8948" reason={metaStrategy.pending.reason}
              time={metaStrategy.pending.timestamp} onApprove={() => metaStrategy.approve(metaStrategy.pending!.id)}
              onReject={() => metaStrategy.reject(metaStrategy.pending!.id)} />
          )}
          {metaGov.pending && (
            <ProposalCard label="Governance" color="#e5534b" reason={metaGov.pending.reason}
              time={metaGov.pending.timestamp} onApprove={() => metaGov.approve(metaGov.pending!.id)}
              onReject={() => metaGov.reject(metaGov.pending!.id)} />
          )}
        </>
      )}

      {/* ── 8. Decision Layers (collapsible) ─────────────────────── */}
      <SectionHeader title="Decision Layers" subtitle="Intent, strategy, meta-strategy, governance, and fabric status"
        open={layersOpen} onToggle={() => setLayersOpen(v => !v)} />

      {layersOpen && (
        <div className="xhud-layers">
          <div className="xhud-layer-row">
            <span className="xhud-layer-label">Intent</span>
            <span className={`xhud-layer-value${intent.currentIntent ? ` xhud-intent--${intent.currentIntent}` : ""}`}>
              {intent.currentIntent ?? "None"}
            </span>
            <span className="xhud-layer-meta">{intent.signalCount} signals</span>
          </div>
          {Object.keys(intent.approvedTuning).length > 0 && (
            <div className="xhud-layer-active">
              <span className="xhud-mini-tag xhud-mini-tag--purple">Intent tuning active</span>
              <button className="xhud-btn xhud-btn--clear-sm" onClick={intent.clearTuning}>Clear</button>
            </div>
          )}

          <div className="xhud-layer-row">
            <span className="xhud-layer-label">Strategy</span>
            <span className={`xhud-layer-value${strategy.approvedStrategy ? ` xhud-strat--${strategy.approvedStrategy}` : ""}`}>
              {strategy.approvedStrategy ?? strategy.evalState.candidate ?? "None"}
            </span>
            {strategy.evalState.candidate && (
              <span className="xhud-layer-meta">Confidence: {Math.round(strategy.evalState.confidence * 100)}%</span>
            )}
          </div>
          {Object.keys(strategy.approvedTuning).length > 0 && (
            <div className="xhud-layer-active">
              <span className="xhud-mini-tag xhud-mini-tag--teal">Strategy active</span>
              <button className="xhud-btn xhud-btn--clear-sm" onClick={strategy.clearTuning}>Clear</button>
            </div>
          )}

          <div className="xhud-layer-row">
            <span className="xhud-layer-label">Meta-Strategy</span>
            <span className="xhud-layer-value">
              {metaStrategy.approvedMeta ?? metaStrategy.evalState.candidate ?? "None"}
            </span>
            {metaStrategy.evalState.candidate && (
              <span className="xhud-layer-meta">Confidence: {Math.round(metaStrategy.evalState.confidence * 100)}%</span>
            )}
            <span className="xhud-layer-meta">{metaStrategy.evalState.history.length} history</span>
          </div>
          {Object.keys(metaStrategy.approvedTuning).length > 0 && (
            <div className="xhud-layer-active">
              <span className="xhud-mini-tag xhud-mini-tag--orange">Meta active</span>
              <button className="xhud-btn xhud-btn--clear-sm" onClick={metaStrategy.clearTuning}>Clear</button>
            </div>
          )}

          <div className="xhud-layer-row">
            <span className="xhud-layer-label">Governance</span>
            <span className={`xhud-layer-value${metaGov.evalState.candidate ? ` xhud-gov-issue--${metaGov.evalState.candidate}` : ""}`}>
              {metaGov.approvedIssue ?? metaGov.evalState.candidate ?? "None"}
            </span>
            {metaGov.evalState.candidate && (
              <span className="xhud-layer-meta">Confidence: {Math.round(metaGov.evalState.confidence * 100)}%</span>
            )}
          </div>
          {Object.keys(metaGov.approvedTuning).length > 0 && (
            <div className="xhud-layer-active">
              <span className="xhud-mini-tag xhud-mini-tag--red">Governance active</span>
              <button className="xhud-btn xhud-btn--clear-sm" onClick={metaGov.clearTuning}>Clear</button>
            </div>
          )}

          <div className="xhud-layer-row">
            <span className="xhud-layer-label">Fabric</span>
            <span className={`xhud-layer-value xhud-fabric--${fabricDashboard.health.label}`}>
              {fabricDashboard.health.label}
            </span>
            <span className="xhud-layer-meta">{fabricDashboard.activeTierCount} tiers</span>
            {fabricDashboard.pendingCount > 0 && <span className="xhud-mini-tag xhud-mini-tag--purple">{fabricDashboard.pendingCount} pending</span>}
            {fabricDashboard.escalationDetected && <span className="xhud-mini-tag xhud-mini-tag--red">Escalation</span>}
            {fabricDashboard.cappingApplied && <span className="xhud-mini-tag xhud-mini-tag--yellow">Capped</span>}
          </div>

          {fabricDashboard.activeTierCount > 0 && (
            <div className="xhud-fabric-tiers">
              {fabricDashboard.activeTiers.map(t => <span key={t} className="xhud-mini-tag xhud-mini-tag--muted">{t}</span>)}
            </div>
          )}

          {fabricDashboard.health.totalDecisions > 0 && (
            <div className="xhud-fabric-stats">
              <span className="xhud-fabric-stat xhud-fabric-stat--good">{fabricDashboard.health.approvals} approved</span>
              <span className="xhud-fabric-stat xhud-fabric-stat--bad">{fabricDashboard.health.rejections} rejected</span>
              <span className="xhud-fabric-stat">{fabricDashboard.health.decisionRate.toFixed(1)}/min</span>
            </div>
          )}

          {fabricDashboard.activeTierCount > 0 && (
            <button className="xhud-btn xhud-btn--danger-full" onClick={fabricClearAll}>Clear All Tuning</button>
          )}
        </div>
      )}

      {/* ── 9. Telemetry, Analytics, Adaptation (collapsible) ────── */}
      <SectionHeader title={`Telemetry (${telemetry.length})`} subtitle="Recent system events"
        open={telemetryOpen} onToggle={() => setTelemetryOpen(v => !v)} />

      {telemetryOpen && (
        <div className="xhud-telemetry">
          {visibleEvents.length === 0 ? (
            <div className="xhud-empty">No events yet</div>
          ) : visibleEvents.map(ev => (
            <div key={ev.id} className={`xhud-tel-row xhud-tel--${ev.type}`}>
              <span className="xhud-tel-type">{ev.type.replace(/-/g, " ")}</span>
              <span className="xhud-tel-summary">{summarizePayload(ev)}</span>
              <span className="xhud-tel-time">{formatTime(ev.timestamp)}</span>
            </div>
          ))}
        </div>
      )}

      <SectionHeader title="Analytics" subtitle="Rates and quality metrics"
        open={analyticsOpen} onToggle={() => setAnalyticsOpen(v => !v)} />

      {analyticsOpen && (
        <div className="xhud-analytics">
          <HealthBar value={analytics.transitionSmoothness} label="Smoothness" description="How smooth scene transitions are" />
          <div className="xhud-analytics-rates">
            <div className="xhud-rate-item">
              <span className="xhud-rate-label">Narrative density</span>
              <span className="xhud-rate-value">{analytics.narrativeDensity.toFixed(1)}/min</span>
            </div>
            <div className="xhud-rate-item">
              <span className="xhud-rate-label">Governor interventions</span>
              <span className="xhud-rate-value">{analytics.governorInterventionRate.toFixed(1)}/min</span>
            </div>
            <div className="xhud-rate-item">
              <span className="xhud-rate-label">Grammar rejections</span>
              <span className="xhud-rate-value">{analytics.grammarRejectionRate.toFixed(1)}/min</span>
            </div>
          </div>
        </div>
      )}

      <SectionHeader
        title={`Adaptation${adaptation.reasons.length > 0 ? ` (${adaptation.reasons.length})` : ""}`}
        subtitle="Active behavioral adjustments"
        open={adaptationOpen} onToggle={() => setAdaptationOpen(v => !v)} />

      {adaptationOpen && (
        <div className="xhud-adaptation">
          {adaptation.reasons.length === 0 ? (
            <div className="xhud-empty">No active adjustments</div>
          ) : adaptation.reasons.map((r, i) => (
            <div key={i} className="xhud-adapt-row">
              <span className="xhud-mini-tag xhud-mini-tag--green">{r.trigger}</span>
              <span className="xhud-adapt-action">{r.action}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── 10. Controls ──────────────────────────────────────────── */}
      <SectionHeader title="Controls" subtitle="Override posture and governor behavior" />

      <div className="xhud-controls">
        <div className="xhud-control-group">
          <span className="xhud-control-label">Posture Override</span>
          <div className="xhud-control-options">
            {POSTURE_OPTIONS.map(p => (
              <button
                key={p}
                className={`xhud-btn xhud-btn--option ${postureNudge === p ? "xhud-btn--option-active" : ""}`}
                onClick={() => onNudgePosture(postureNudge === p ? null : p)}
                title={POSTURE_DESCRIPTIONS[p]}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="xhud-control-group">
          <span className="xhud-control-label">Governor</span>
          <div className="xhud-control-options">
            <button className="xhud-btn xhud-btn--option" onClick={onToggleGovernor}>
              {governorDisplay.enabled ? "Disable" : "Enable"}
            </button>
            {PRESET_OPTIONS.map(p => (
              <button
                key={p}
                className={`xhud-btn xhud-btn--option ${governorPreset === p ? "xhud-btn--option-active" : ""}`}
                onClick={() => onSetPreset(p)}
                title={PRESET_DESCRIPTIONS[p]}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
