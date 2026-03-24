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
import "./ExpressiveHud.css";

export const EXPRESSIVE_HUD_ENABLED = true;

const POSTURE_OPTIONS: DaedalusPosture[] = ["companion", "sentinel", "observer", "dormant"];
const PRESET_OPTIONS: GovernorPresetName[] = ["default", "calm", "responsive"];

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
}

function formatAge(ms: number): string {
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m`;
  return `${(ms / 3_600_000).toFixed(1)}h`;
}

const TELEMETRY_VISIBLE_COUNT = 8;

function formatTime(ts: number): string {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

export function ExpressiveHud({
  scene,
  grammar,
  frameId,
  persistence,
  telemetry,
  analytics,
  adaptation,
  autonomy,
  intent,
  strategy,
  metaStrategy,
  metaGov,
  fabricDashboard,
  fabricClearAll,
  halo,
  crown,
  kernelRollback,
  governorDisplay,
  timeline,
  affect,
  governorPreset,
  postureNudge,
  onToggleGovernor,
  onSetPreset,
  onNudgePosture,
}: Props) {
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [adaptationOpen, setAdaptationOpen] = useState(false);
  const [hudCollapsed, setHudCollapsed] = useState(true);

  if (!EXPRESSIVE_HUD_ENABLED) return null;

  const visibleEvents = telemetry.slice(-TELEMETRY_VISIBLE_COUNT).reverse();

  return (
    <div className={`expressive-hud cin-arrive${hudCollapsed ? " expressive-hud--collapsed" : ""}`}>
      <div className="hud-title" onClick={() => setHudCollapsed((v) => !v)} style={{ cursor: "pointer" }}>
        <span>Expressive HUD</span>
        <span className={`hud-scene-name hud-scene--${scene.sceneName}`}>{scene.sceneName}</span>
        <span className="hud-frame-id">{hudCollapsed ? "▸" : "▾"} f{frameId}</span>
      </div>

      <div className={`hud-kernel-bar hud-kernel--${halo.kernelStatus}${halo.shellStatus === "degraded" ? " hud-shell--degraded" : ""}`}>
        <span
          className={`hud-crown hud-crown--${crown.symbol}`}
          style={{
            opacity: 0.5 + crown.glow * 0.5,
            animationDuration: crown.pulse > 0 ? `${1.8 - crown.pulse * 1.2}s` : "0s",
          }}
          title={`${crown.symbol} — glow ${crown.glow.toFixed(2)} stability ${crown.stability.toFixed(2)}`}
        >
          {crown.symbol}
        </span>
        <span className={`hud-shell-status hud-shell--${halo.shellStatus}`}>{halo.shellStatus}</span>
        <span className="hud-kernel-status">{halo.kernelStatus}</span>
        <span
          className={`hud-kernel-invariants ${halo.invariantsPassed ? "hud-invariants--ok" : "hud-invariants--fail"}`}
          title={halo.invariantsPassed
            ? `${halo.invariantsTotal} invariants held`
            : `${halo.failedInvariants.length} invariant${halo.failedInvariants.length !== 1 ? "s" : ""} violated: ${halo.failedInvariants.join(", ")}`
          }
        >
          {`${halo.invariantsHeld}/${halo.invariantsTotal}`}
        </span>
        {halo.overrideCount > 0 && (
          <span className="hud-kernel-overrides">
            {halo.overrideCount} override{halo.overrideCount !== 1 ? "s" : ""}
          </span>
        )}
        {halo.pendingCount > 0 && (
          <span className="hud-kernel-pending">
            {halo.pendingCount} pending
          </span>
        )}
        {halo.kernelStatus !== "clean" && (
          <button className="hud-btn hud-btn--kernel-rollback" onClick={kernelRollback}>
            Rollback
          </button>
        )}
      </div>

      <div className="hud-grid">
        <div className="hud-cell">
          <span className="hud-label">Posture</span>
          <span className={`hud-value hud-posture--${scene.posture}`}>{scene.posture}</span>
        </div>
        <div className="hud-cell">
          <span className="hud-label">Affect</span>
          <span className="hud-value">{affect}</span>
        </div>
        <div className="hud-cell">
          <span className="hud-label">Mode</span>
          <span className={`hud-value hud-mode--${scene.mode}`}>{scene.mode}</span>
        </div>
        <div className="hud-cell">
          <span className="hud-label">Tone</span>
          <span className={`hud-value hud-tone--${scene.tone}`}>{scene.tone}</span>
        </div>
      </div>

      <div className="hud-scalars">
        <span className="hud-scalar">
          <span className="hud-label">Glow</span>
          <span className="hud-bar" style={{ width: `${scene.glow * 100}%` }} />
          <span className="hud-num">{scene.glow.toFixed(2)}</span>
        </span>
        <span className="hud-scalar">
          <span className="hud-label">Motion</span>
          <span className="hud-bar" style={{ width: `${scene.motion * 100}%` }} />
          <span className="hud-num">{scene.motion.toFixed(2)}</span>
        </span>
      </div>

      {scene.continuityBadge && (
        <div className="hud-badge">
          <span className="hud-label">Badge</span>
          <span className="hud-value">{scene.continuityBadge.label}</span>
        </div>
      )}

      <div className="hud-divider" />

      <div className="hud-timeline-row">
        <span className={`hud-value hud-phase--${timeline.phase}`}>{timeline.phase}</span>
        <span className="hud-scalar hud-scalar--inline">
          <span className="hud-label">Mom</span>
          <span className="hud-bar hud-bar--momentum" style={{ width: `${timeline.momentum * 100}%` }} />
          <span className="hud-num">{timeline.momentum.toFixed(2)}</span>
        </span>
        <span className="hud-tag hud-tag--events">{timeline.eventCount}ev</span>
      </div>

      {scene.narrativeLine && (
        <div className={`hud-narrative hud-narrative--${scene.tone}`}>
          {scene.narrativeLine}
        </div>
      )}

      <div className="hud-grammar-row">
        {grammar.blendMs > 0 && (
          <span className="hud-tag hud-tag--blend">{grammar.blendMs}ms</span>
        )}
        {grammar.narrativeSync && (
          <span className="hud-tag hud-tag--sync">sync</span>
        )}
        {!grammar.allowed && (
          <span className="hud-tag hud-tag--blocked">held</span>
        )}
        {scene.progress < 1 && (
          <span className="hud-scalar hud-scalar--inline">
            <span className="hud-bar hud-bar--progress" style={{ width: `${scene.progress * 100}%` }} />
            <span className="hud-num">{(scene.progress * 100).toFixed(0)}%</span>
          </span>
        )}
      </div>

      <div className="hud-divider" />

      <div className="hud-governor-row">
        <span className={`hud-indicator ${governorDisplay.enabled ? "hud-indicator--on" : "hud-indicator--off"}`}>
          Gov {governorDisplay.enabled ? "ON" : "OFF"}
        </span>
        {governorDisplay.escalationLocked && <span className="hud-tag hud-tag--lock">Lock</span>}
        {governorDisplay.modeCooldownActive && <span className="hud-tag hud-tag--cooldown">Mode CD</span>}
        {governorDisplay.toneCooldownActive && <span className="hud-tag hud-tag--cooldown">Tone CD</span>}
      </div>

      {persistence.restoredFrom && (
        <div className="hud-persistence-row">
          <span className="hud-tag hud-tag--restored">restored</span>
          <span className="hud-value">{persistence.restoredFrom.sceneName}</span>
          <span className="hud-num">{formatAge(persistence.ageMs!)}</span>
        </div>
      )}

      <div className="hud-divider" />

      <button
        className="hud-section-toggle"
        onClick={() => setTelemetryOpen((v) => !v)}
      >
        Telemetry ({telemetry.length}) {telemetryOpen ? "▾" : "▸"}
      </button>

      {telemetryOpen && (
        <div className="hud-telemetry-log">
          {visibleEvents.length === 0 && (
            <div className="hud-telemetry-empty">No events yet</div>
          )}
          {visibleEvents.map((ev) => (
            <div key={ev.id} className={`hud-telemetry-row hud-tel--${ev.type}`}>
              <span className="hud-tel-type">{ev.type}</span>
              <span className="hud-tel-summary">{summarizePayload(ev)}</span>
              <span className="hud-tel-time">{formatTime(ev.timestamp)}</span>
            </div>
          ))}
        </div>
      )}

      <button
        className="hud-section-toggle"
        onClick={() => setAnalyticsOpen((v) => !v)}
      >
        Analytics {analyticsOpen ? "▾" : "▸"}
      </button>

      {analyticsOpen && (
        <div className="hud-analytics-grid">
          <div className="hud-analytics-row">
            <span className="hud-label">Health</span>
            <span className="hud-bar hud-bar--health" style={{ width: `${analytics.expressiveHealth * 100}%` }} />
            <span className="hud-num">{analytics.expressiveHealth.toFixed(2)}</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Stability</span>
            <span className="hud-bar" style={{ width: `${analytics.sceneStability * 100}%` }} />
            <span className="hud-num">{analytics.sceneStability.toFixed(2)}</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Smooth</span>
            <span className="hud-bar" style={{ width: `${analytics.transitionSmoothness * 100}%` }} />
            <span className="hud-num">{analytics.transitionSmoothness.toFixed(2)}</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Volatility</span>
            <span className="hud-bar hud-bar--warn" style={{ width: `${analytics.momentumVolatility * 100}%` }} />
            <span className="hud-num">{analytics.momentumVolatility.toFixed(2)}</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Narrative</span>
            <span className="hud-num hud-num--rate">{analytics.narrativeDensity.toFixed(1)}/min</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Gov rate</span>
            <span className="hud-num hud-num--rate">{analytics.governorInterventionRate.toFixed(1)}/min</span>
          </div>
          <div className="hud-analytics-row">
            <span className="hud-label">Rejections</span>
            <span className="hud-num hud-num--rate">{analytics.grammarRejectionRate.toFixed(1)}/min</span>
          </div>
        </div>
      )}

      <button
        className="hud-section-toggle"
        onClick={() => setAdaptationOpen((v) => !v)}
      >
        Adaptation {adaptation.reasons.length > 0 ? `(${adaptation.reasons.length})` : ""} {adaptationOpen ? "▾" : "▸"}
      </button>

      {adaptationOpen && (
        <div className="hud-adaptation-log">
          {adaptation.reasons.length === 0 && (
            <div className="hud-telemetry-empty">No active adjustments</div>
          )}
          {adaptation.reasons.map((r, i) => (
            <div key={i} className="hud-adaptation-row">
              <span className="hud-tag hud-tag--adapt">{r.trigger}</span>
              <span className="hud-tel-summary">{r.action}</span>
            </div>
          ))}
        </div>
      )}

      {autonomy.pending && (
        <div className="hud-autonomy-card">
          <div className="hud-autonomy-header">
            <span className="hud-tag hud-tag--proposal">Proposal</span>
            <span className="hud-tel-time">{formatTime(autonomy.pending.timestamp)}</span>
          </div>
          <div className="hud-autonomy-reason">{autonomy.pending.reason}</div>
          <div className="hud-autonomy-actions">
            <button
              className="hud-btn hud-btn--approve"
              onClick={() => autonomy.approve(autonomy.pending!.id)}
            >
              Approve
            </button>
            <button
              className="hud-btn hud-btn--reject"
              onClick={() => autonomy.reject(autonomy.pending!.id)}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {Object.keys(autonomy.approvedTuning).length > 0 && (
        <div className="hud-autonomy-active">
          <span className="hud-tag hud-tag--approved">autonomy active</span>
          <button className="hud-btn hud-btn--small" onClick={autonomy.clearTuning}>
            Clear
          </button>
        </div>
      )}

      <div className="hud-intent-row">
        <span className="hud-label">Intent</span>
        <span className={`hud-tag hud-tag--intent${intent.currentIntent ? ` hud-intent--${intent.currentIntent}` : ""}`}>
          {intent.currentIntent ?? "—"}
        </span>
        <span className="hud-num--rate">{intent.signalCount} sig</span>
      </div>

      {intent.pending && (
        <div className="hud-autonomy-card hud-intent-card">
          <div className="hud-autonomy-header">
            <span className="hud-tag hud-tag--intent-proposal">Intent Proposal</span>
            <span className="hud-tel-time">{formatTime(intent.pending.timestamp)}</span>
          </div>
          <div className="hud-autonomy-reason">{intent.pending.reason}</div>
          <div className="hud-autonomy-actions">
            <button
              className="hud-btn hud-btn--approve"
              onClick={() => intent.approve(intent.pending!.id)}
            >
              Approve
            </button>
            <button
              className="hud-btn hud-btn--reject"
              onClick={() => intent.reject(intent.pending!.id)}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {Object.keys(intent.approvedTuning).length > 0 && (
        <div className="hud-autonomy-active">
          <span className="hud-tag hud-tag--intent-active">intent active</span>
          <button className="hud-btn hud-btn--small" onClick={intent.clearTuning}>
            Clear
          </button>
        </div>
      )}

      <div className="hud-strategy-row">
        <span className="hud-label">Strategy</span>
        <span className={`hud-tag hud-tag--strategy${strategy.approvedStrategy ? ` hud-strategy--${strategy.approvedStrategy}` : ""}`}>
          {strategy.approvedStrategy ?? strategy.evalState.candidate ?? "—"}
        </span>
        {strategy.evalState.candidate && (
          <span className="hud-num--rate">
            {(strategy.evalState.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {strategy.pending && (
        <div className="hud-autonomy-card hud-strategy-card">
          <div className="hud-autonomy-header">
            <span className="hud-tag hud-tag--strategy-proposal">Strategy</span>
            <span className="hud-tel-time">{formatTime(strategy.pending.timestamp)}</span>
          </div>
          <div className="hud-autonomy-reason">{strategy.pending.reason}</div>
          <div className="hud-autonomy-actions">
            <button
              className="hud-btn hud-btn--approve"
              onClick={() => strategy.approve(strategy.pending!.id)}
            >
              Approve
            </button>
            <button
              className="hud-btn hud-btn--reject"
              onClick={() => strategy.reject(strategy.pending!.id)}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {Object.keys(strategy.approvedTuning).length > 0 && (
        <div className="hud-autonomy-active">
          <span className="hud-tag hud-tag--strategy-active">
            {strategy.approvedStrategy ?? "strategy"} active
          </span>
          <button className="hud-btn hud-btn--small" onClick={strategy.clearTuning}>
            Clear
          </button>
        </div>
      )}

      <div className="hud-meta-row">
        <span className="hud-label">Meta</span>
        <span className={`hud-tag hud-tag--meta${metaStrategy.approvedMeta ? ` hud-meta--${metaStrategy.approvedMeta}` : ""}`}>
          {metaStrategy.approvedMeta ?? metaStrategy.evalState.candidate ?? "—"}
        </span>
        {metaStrategy.evalState.candidate && (
          <span className="hud-num--rate">
            {(metaStrategy.evalState.confidence * 100).toFixed(0)}%
          </span>
        )}
        <span className="hud-num--rate">
          {metaStrategy.evalState.history.length} hist
        </span>
      </div>

      {metaStrategy.pending && (
        <div className="hud-autonomy-card hud-meta-card">
          <div className="hud-autonomy-header">
            <span className="hud-tag hud-tag--meta-proposal">Meta-Strategy</span>
            <span className="hud-tel-time">{formatTime(metaStrategy.pending.timestamp)}</span>
          </div>
          <div className="hud-autonomy-reason">{metaStrategy.pending.reason}</div>
          <div className="hud-autonomy-actions">
            <button
              className="hud-btn hud-btn--approve"
              onClick={() => metaStrategy.approve(metaStrategy.pending!.id)}
            >
              Approve
            </button>
            <button
              className="hud-btn hud-btn--reject"
              onClick={() => metaStrategy.reject(metaStrategy.pending!.id)}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {Object.keys(metaStrategy.approvedTuning).length > 0 && (
        <div className="hud-autonomy-active">
          <span className="hud-tag hud-tag--meta-active">
            {metaStrategy.approvedMeta ?? "meta"} active
          </span>
          <button className="hud-btn hud-btn--small" onClick={metaStrategy.clearTuning}>
            Clear
          </button>
        </div>
      )}

      <div className="hud-gov-row">
        <span className="hud-label">Gov</span>
        <span className={`hud-tag hud-tag--gov${metaGov.evalState.candidate ? ` hud-gov--${metaGov.evalState.candidate}` : ""}`}>
          {metaGov.approvedIssue ?? metaGov.evalState.candidate ?? "—"}
        </span>
        {metaGov.evalState.candidate && (
          <span className="hud-num--rate">
            {(metaGov.evalState.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {metaGov.pending && (
        <div className="hud-autonomy-card hud-gov-card">
          <div className="hud-autonomy-header">
            <span className="hud-tag hud-tag--gov-proposal">Governance</span>
            <span className="hud-tel-time">{formatTime(metaGov.pending.timestamp)}</span>
          </div>
          <div className="hud-autonomy-reason">{metaGov.pending.reason}</div>
          <div className="hud-autonomy-actions">
            <button
              className="hud-btn hud-btn--approve"
              onClick={() => metaGov.approve(metaGov.pending!.id)}
            >
              Approve
            </button>
            <button
              className="hud-btn hud-btn--reject"
              onClick={() => metaGov.reject(metaGov.pending!.id)}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {Object.keys(metaGov.approvedTuning).length > 0 && (
        <div className="hud-autonomy-active">
          <span className="hud-tag hud-tag--gov-active">
            {metaGov.approvedIssue ?? "governance"} active
          </span>
          <button className="hud-btn hud-btn--small" onClick={metaGov.clearTuning}>
            Clear
          </button>
        </div>
      )}

      <div className="hud-fabric-row">
        <span className="hud-label">Fabric</span>
        <span className={`hud-tag hud-tag--fabric-health hud-fabric--${fabricDashboard.health.label}`}>
          {fabricDashboard.health.label}
        </span>
        <span className="hud-num--rate">{fabricDashboard.activeTierCount} tiers</span>
        {fabricDashboard.pendingCount > 0 && (
          <span className="hud-tag hud-tag--fabric-pending">
            {fabricDashboard.pendingCount} pending
          </span>
        )}
        {fabricDashboard.escalationDetected && (
          <span className="hud-tag hud-tag--fabric-escalation">escalation</span>
        )}
        {fabricDashboard.cappingApplied && (
          <span className="hud-tag hud-tag--fabric-capped">capped</span>
        )}
      </div>
      {fabricDashboard.activeTierCount > 0 && (
        <div className="hud-fabric-tiers">
          {fabricDashboard.activeTiers.map((t) => (
            <span key={t} className="hud-tag hud-tag--fabric-tier">{t}</span>
          ))}
        </div>
      )}
      {fabricDashboard.health.totalDecisions > 0 && (
        <div className="hud-fabric-decisions">
          <span className="hud-num--rate">
            {fabricDashboard.health.approvals}&#10003;
          </span>
          <span className="hud-num--rate">
            {fabricDashboard.health.rejections}&#10007;
          </span>
          <span className="hud-fabric-rate">
            {fabricDashboard.health.decisionRate.toFixed(1)}/min
          </span>
        </div>
      )}
      {fabricDashboard.activeTierCount > 0 && (
        <button className="hud-btn hud-btn--fabric-clear" onClick={fabricClearAll}>
          Clear All Tuning
        </button>
      )}

      <div className="hud-divider" />

      <div className="hud-section-label">Override Strip</div>

      <div className="hud-override-row">
        <span className="hud-label">Posture</span>
        {POSTURE_OPTIONS.map((p) => (
          <button
            key={p}
            className={`hud-btn ${postureNudge === p ? "hud-btn--active" : ""}`}
            onClick={() => onNudgePosture(postureNudge === p ? null : p)}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="hud-override-row">
        <span className="hud-label">Governor</span>
        <button className="hud-btn" onClick={onToggleGovernor}>
          {governorDisplay.enabled ? "Disable" : "Enable"}
        </button>
        {PRESET_OPTIONS.map((p) => (
          <button
            key={p}
            className={`hud-btn ${governorPreset === p ? "hud-btn--active" : ""}`}
            onClick={() => onSetPreset(p)}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
