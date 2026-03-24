import { useState, useCallback, useMemo, useRef } from "react";
import { useDaedalusOrchestrator } from "../hooks/useDaedalusOrchestrator";
import { useDaedalusEvents } from "../hooks/useDaedalusEvents";
import type { DaedalusEventPayload } from "../hooks/useDaedalusEvents";
import { useBeingPresences } from "../hooks/useBeingPresences";
import { useExpressiveField } from "../hooks/useExpressiveField";
import { useOrchestration } from "../hooks/useOrchestration";
import { useOperatorAffect } from "../hooks/useOperatorAffect";
import type { PostureState, DaedalusPosture } from "../shared/daedalus/contracts";
import { GOVERNOR_PRESETS } from "../shared/daedalus/governor";
import type { GovernorPresetName } from "../shared/daedalus/governor";
import { PostureBanner } from "./PostureBanner";
import { GovernancePanel } from "./GovernancePanel";
import { ExpressiveFieldView } from "./ExpressiveFieldView";
import { NegotiationPreviewPanel } from "./NegotiationPreviewPanel";
import { BeingPresencePanel } from "./BeingPresencePanel";
import { EmbodimentAvatar } from "./EmbodimentAvatar";
import { AttentionHalo } from "./AttentionHalo";
import { CockpitOverlay } from "./CockpitOverlay";
import { AffectStrip } from "./AffectStrip";
import { ContinuityRibbon } from "./ContinuityRibbon";
import { ExpressiveHud } from "./ExpressiveHud";
import { KernelThrone } from "./KernelThrone";
import { KernelRite } from "./KernelRite";
import { useContinuitySignals } from "../hooks/useContinuitySignals";
import { useConductor } from "../hooks/useConductor";
import { useGovernor } from "../hooks/useGovernor";
import { useTimeline } from "../hooks/useTimeline";
import { useNarrative } from "../hooks/useNarrative";
import { useFusion } from "../hooks/useFusion";
import { useSceneGrammar } from "../hooks/useSceneGrammar";
import { useSceneSync } from "../hooks/useSceneSync";
import { useScenePersistence } from "../hooks/useScenePersistence";
import { useSceneTelemetry } from "../hooks/useSceneTelemetry";
import { useSceneAnalytics } from "../hooks/useSceneAnalytics";
import { useSceneAdaptation } from "../hooks/useSceneAdaptation";
import { useSceneAutonomy } from "../hooks/useSceneAutonomy";
import { useIntentModel } from "../hooks/useIntentModel";
import { useExpressiveStrategy } from "../hooks/useExpressiveStrategy";
import { useMetaStrategy } from "../hooks/useMetaStrategy";
import { useMetaGovernance } from "../hooks/useMetaGovernance";
import { usePostAutonomy } from "../hooks/usePostAutonomy";
import { useGovernanceFabric } from "../hooks/useGovernanceFabric";
import { useKernelShell } from "../hooks/useKernelShell";
import { useConnectivityEpistemic } from "../hooks/useConnectivityEpistemic";
import { useOperatorContext } from "../hooks/useOperatorContext";
import { useEmbodiedPresence } from "../hooks/useEmbodiedPresence";
import { useNodePresence } from "../hooks/useNodePresence";
import { useAttentionTask } from "../hooks/useAttentionTask";
import { useSystemContinuity } from "../hooks/useSystemContinuity";
import { usePreSealValidation } from "../hooks/usePreSealValidation";
import { mergeAutonomyTuning } from "../shared/daedalus/sceneAutonomyEngine";
import type { TimelineConfig } from "../shared/daedalus/timeline";
import { TIMELINE_DEFAULTS } from "../shared/daedalus/timeline";
import type { NarrativeConfig } from "../shared/daedalus/narrative";
import { NARRATIVE_DEFAULTS } from "../shared/daedalus/narrative";
import type { SceneGrammarConfig } from "../shared/daedalus/sceneGrammar";
import { SCENE_GRAMMAR_DEFAULTS } from "../shared/daedalus/sceneGrammar";
import { ANALYTICS_IDLE } from "../shared/daedalus/sceneAnalytics";
import NodeCapabilitiesPanel from "./NodeCapabilitiesPanel";
import type { NodeInfo } from "./NodeCapabilitiesPanel";
import "./DaedalusOrchestratorPanel.css";
import "../styles/cinematics.css";
import "../styles/operator-affect.css";
import "../styles/conductor.css";
import "../styles/scene-surfaces.css";

type ActivePanel = "topology" | "field" | "governance" | "beings";

const MAX_GOV_EVENTS = 50;

function DaedalusOrchestratorPanel() {
  const {
    snapshot,
    loadingSnapshot,
    snapshotError,
    lastSnapshotAt,
    selectedTrace,
    loadingTrace,
    traceError,
    negotiationMessage,
    loadingNegotiation,
    selectCapability,
    reload,
    sseEvent,
    sseConnected,
    highlightNodeId,
  } = useDaedalusOrchestrator();

  const beings = useBeingPresences();
  const expressive = useExpressiveField(beings);
  const orchestration = useOrchestration(expressive);

  const dominantSignal = expressive.behavioral.signals.find(
    (s) => s.beingId === expressive.behavioral.dominantBeingId,
  );

  const continuityLabel =
    orchestration.affect.stability > 0.8
      ? "stable"
      : orchestration.affect.stability > 0.4
        ? "shifting"
        : "fragile";

  const [activePanel, setActivePanel] = useState<ActivePanel>("topology");
  const [govEvents, setGovEvents] = useState<DaedalusEventPayload[]>([]);
  const [govPosture, setGovPosture] = useState<PostureState>("OPEN");

  useDaedalusEvents(useCallback((event: DaedalusEventPayload) => {
    if (
      event.type === "POSTURE_CHANGED" ||
      event.type === "GOVERNANCE_OVERRIDE_APPLIED" ||
      event.type === "CONTINUITY_DRIFT_DETECTED"
    ) {
      setGovEvents((prev) => [...prev.slice(-(MAX_GOV_EVENTS - 1)), event]);
    }
    if (event.type === "POSTURE_CHANGED" && event.posture) {
      setGovPosture(event.posture as PostureState);
    }
  }, []));

  const { affect, pin, unpin } = useOperatorAffect({
    orchestration,
    governancePosture: govPosture,
    activePanel,
  });

  const continuitySignals = useContinuitySignals(beings);

  const [governorEnabled, setGovernorEnabled] = useState(true);
  const [governorPreset, setGovernorPreset] = useState<GovernorPresetName>("default");
  const [postureNudge, setPostureNudge] = useState<DaedalusPosture | null>(null);

  // ── Full autonomy stack: adaptation → t0 → t1 → t3 → t4 → t5 ──
  const prevAnalyticsRef = useRef(ANALYTICS_IDLE);
  const adaptation = useSceneAdaptation(prevAnalyticsRef.current);
  const autonomy = useSceneAutonomy(prevAnalyticsRef.current);
  const intent = useIntentModel();
  const strategy = useExpressiveStrategy(prevAnalyticsRef.current, intent.currentIntent);
  const metaStrategy = useMetaStrategy(prevAnalyticsRef.current, strategy.approvedStrategy);
  const metaGov = useMetaGovernance(
    prevAnalyticsRef.current,
    strategy.approvedStrategy,
    metaStrategy.approvedMeta,
  );
  const rawTuning = useMemo(
    () =>
      mergeAutonomyTuning(
        mergeAutonomyTuning(
          mergeAutonomyTuning(
            mergeAutonomyTuning(
              mergeAutonomyTuning(adaptation.tuning, autonomy.approvedTuning),
              intent.approvedTuning,
            ),
            strategy.approvedTuning,
          ),
          metaStrategy.approvedTuning,
        ),
        metaGov.approvedTuning,
      ),
    [
      adaptation.tuning,
      autonomy.approvedTuning,
      intent.approvedTuning,
      strategy.approvedTuning,
      metaStrategy.approvedTuning,
      metaGov.approvedTuning,
    ],
  );

  // ── Post-Autonomy: safety-cap the merged tuning ──
  const tierTunings = useMemo(
    () => ({
      adaptation: adaptation.tuning,
      "tier-0": autonomy.approvedTuning,
      "tier-1": intent.approvedTuning,
      "tier-3": strategy.approvedTuning,
      "tier-4": metaStrategy.approvedTuning,
      "tier-5": metaGov.approvedTuning,
    }),
    [
      adaptation.tuning,
      autonomy.approvedTuning,
      intent.approvedTuning,
      strategy.approvedTuning,
      metaStrategy.approvedTuning,
      metaGov.approvedTuning,
    ],
  );
  const postAutonomyFabric = usePostAutonomy(rawTuning, tierTunings);
  const tuning = postAutonomyFabric.effectiveTuning;

  // ── Governance Fabric: unified dashboard over the full autonomy stack ──
  const allDecisions = useMemo(
    () => [
      ...autonomy.decisions,
      ...intent.decisions,
      ...strategy.decisions,
      ...metaStrategy.decisions,
      ...metaGov.decisions,
    ],
    [autonomy.decisions, intent.decisions, strategy.decisions, metaStrategy.decisions, metaGov.decisions],
  );
  const pendingCount = [
    autonomy.pending,
    intent.pending,
    strategy.pending,
    metaStrategy.pending,
    metaGov.pending,
  ].filter(Boolean).length;
  const clearFns = useMemo(
    () => [
      autonomy.clearTuning,
      intent.clearTuning,
      strategy.clearTuning,
      metaStrategy.clearTuning,
      metaGov.clearTuning,
    ],
    [autonomy.clearTuning, intent.clearTuning, strategy.clearTuning, metaStrategy.clearTuning, metaGov.clearTuning],
  );
  const { dashboard: fabricDashboard, clearAll: fabricClearAll } = useGovernanceFabric(
    postAutonomyFabric,
    allDecisions,
    pendingCount,
    clearFns,
  );

  // ── Governance Kernel: apex state + rollback ──
  const rejectAllPending = useCallback(() => {
    if (autonomy.pending) autonomy.reject(autonomy.pending.id);
    if (intent.pending) intent.reject(intent.pending.id);
    if (strategy.pending) strategy.reject(strategy.pending.id);
    if (metaStrategy.pending) metaStrategy.reject(metaStrategy.pending.id);
    if (metaGov.pending) metaGov.reject(metaGov.pending.id);
  }, [autonomy, intent, strategy, metaStrategy, metaGov]);
  const { halo, crown, throne, rollback: kernelRollback } = useKernelShell(
    tuning,
    fabricDashboard,
    fabricClearAll,
    rejectAllPending,
  );

  const operatorCtx = useOperatorContext({
    activePanel,
    affectEffective: affect.effective,
    affectPinned: affect.pinned !== null,
    currentIntent: intent.currentIntent,
    postureNudge: postureNudge,
    governorEnabled,
    governorPreset,
    pendingProposals: pendingCount,
  });

  const governorConfig = useMemo(
    () => ({
      ...GOVERNOR_PRESETS[governorPreset],
      enabled: governorEnabled,
      ...(tuning.governorCooldownMs !== undefined && { cooldownMs: tuning.governorCooldownMs }),
      ...(tuning.governorEscalationLockMs !== undefined && { escalationLockMs: tuning.governorEscalationLockMs }),
    }),
    [governorPreset, governorEnabled, tuning.governorCooldownMs, tuning.governorEscalationLockMs],
  );

  const timelineConfig = useMemo(
    (): TimelineConfig => ({
      ...TIMELINE_DEFAULTS,
      ...(tuning.timelineMomentumHalfLifeMs !== undefined && { momentumHalfLifeMs: tuning.timelineMomentumHalfLifeMs }),
    }),
    [tuning.timelineMomentumHalfLifeMs],
  );

  const narrativeConfig = useMemo(
    (): NarrativeConfig => ({
      ...NARRATIVE_DEFAULTS,
      ...(tuning.narrativeMinIntervalMs !== undefined && { minIntervalMs: tuning.narrativeMinIntervalMs }),
    }),
    [tuning.narrativeMinIntervalMs],
  );

  const grammarConfig = useMemo(
    (): SceneGrammarConfig => ({
      ...SCENE_GRAMMAR_DEFAULTS,
      ...(tuning.grammarDefaultDwellMs !== undefined && { defaultDwellMs: tuning.grammarDefaultDwellMs }),
      ...(tuning.grammarDefaultBlendMs !== undefined && { defaultBlendMs: tuning.grammarDefaultBlendMs }),
    }),
    [tuning.grammarDefaultDwellMs, tuning.grammarDefaultBlendMs],
  );

  const effectiveOrchestration = useMemo(
    () => postureNudge ? { ...orchestration, orchestratedPosture: postureNudge } : orchestration,
    [orchestration, postureNudge],
  );

  const rawConductor = useConductor(effectiveOrchestration, affect, expressive, continuitySignals);
  const { output: governed, display: governorDisplay } = useGovernor(rawConductor, governorConfig);
  const { output: conductor, snapshot: timelineSnapshot } = useTimeline(governed, timelineConfig);
  const narrative = useNarrative(conductor, timelineSnapshot, affect.effective, narrativeConfig);
  const rawScene = useFusion(conductor, narrative, timelineSnapshot, affect.effective);
  const { scene: grammarScene, grammar: sceneGrammar } = useSceneGrammar(rawScene, grammarConfig);
  const frame = useSceneSync(grammarScene, sceneGrammar);
  const { scene, surfaces: surfaceProps, cssVars: surfaceCssVars } = frame;
  const persistence = useScenePersistence(frame, timelineSnapshot);
  const telemetry = useSceneTelemetry({
    scene,
    grammar: sceneGrammar,
    timeline: timelineSnapshot,
    governorDisplay,
    persistence,
  });
  const analytics = useSceneAnalytics(telemetry);
  prevAnalyticsRef.current = analytics;

  const nodes: NodeInfo[] =
    snapshot?.nodes.map((n) => ({
      id: n.id,
      status: n.status,
      lastHeartbeat: n.lastHeartbeat,
      glow: n.glow,
      risk: n.risk,
      capabilities: n.capabilities.map((c) => ({
        name: c.name,
        value: c.value,
        enabled: c.enabled,
      })),
    })) ?? [];

  const rawConnNodes = useMemo(
    () =>
      snapshot?.nodes.map((n) => ({
        id: n.id,
        status: n.status,
        lastHeartbeat: n.lastHeartbeat,
        risk: n.risk,
        capabilities: n.capabilities,
      })) ?? [],
    [snapshot],
  );
  const { connectivity, epistemic } = useConnectivityEpistemic(rawConnNodes, sseConnected);

  const embodied = useEmbodiedPresence({
    beingCount: Object.keys(beings).length,
    dominantBeingId: expressive.behavioral.dominantBeingId,
    posture: expressive.posture,
    arousal: expressive.arousal,
    focus: expressive.focus,
    stability: expressive.stability,
    sceneGlow: scene.glow,
    sceneMotion: scene.motion,
    connectivityNodes: connectivity.nodes,
  });

  const nodePresence = useNodePresence(connectivity);

  const attentionTask = useAttentionTask({
    expressiveAttentionLevel: expressive.attention.level,
    expressiveFocus: expressive.focus,
    expressiveArousal: expressive.arousal,
    expressiveStability: expressive.stability,
    orchestrationIntent: orchestration.intent,
    activePanel: activePanel,
    operatorIntent: intent.currentIntent,
    pendingProposals: pendingCount,
  });

  const bestStreak = useMemo(
    () => Math.max(0, ...Object.values(beings).map((b) => b.continuity.streak)),
    [beings],
  );
  const driftSignalCount = useMemo(
    () => continuitySignals.filter((s) => s.kind === "drift-recovery").length,
    [continuitySignals],
  );
  const anchorSignal = useMemo(
    () => continuitySignals.find((s) => s.kind === "anchor") ?? null,
    [continuitySignals],
  );

  const sysContinuity = useSystemContinuity({
    beingStability: expressive.stability,
    beingCount: Object.keys(beings).length,
    bestStreak,
    driftSignalCount,
    anchorBeingId: anchorSignal?.beingId ?? null,
    orchestrationStability: orchestration.affect.stability,
    continuityBlend: orchestration.transition.continuityBlend,
    embodiedContinuity: embodied.continuity,
    motionGrammar: embodied.motionGrammar,
    timelineMomentum: timelineSnapshot.momentum,
    persistenceRestored: persistence.restoredFrom !== null,
  });

  const preSeal = usePreSealValidation({
    throne,
    connectivity,
    epistemic,
    operator: operatorCtx,
    embodied,
    nodePresence,
    attentionTask,
    continuity: sysContinuity,
  });

  const liveLine =
    sseEvent && sseEvent.type === "NEGOTIATION_COMPLETED"
      ? {
          timestamp: sseEvent.timestamp,
          label: sseEvent.summary ?? "Negotiation completed",
          nodeId: sseEvent.nodeId,
        }
      : null;

  return (
    <div
      className={`daedalus-orchestrator-panel cin-shell cin-intent-${orchestration.intent} affect-${affect.effective} conductor-shell conductor-${scene.mode} conductor-tone-${scene.tone} fusion-scene-${scene.sceneName} surface-ribbon-${surfaceProps.ribbonTone}${scene.suppressAmbientPulse ? " conductor-no-pulse" : ""}`}
      style={surfaceCssVars as React.CSSProperties}
    >
      <div className="daedalus-main cin-arrive">
        <PostureBanner />

        <div className="daedalus-header">
          <div className="daedalus-header__top">
            <h1>Daedalus Orchestrator</h1>
            {loadingSnapshot && <span className="pill pill-loading">Loading…</span>}
            {snapshotError && <span className="pill pill-error">{snapshotError}</span>}
            {lastSnapshotAt && !loadingSnapshot && !snapshotError && (
              <span className="pill pill-fresh">
                Updated {lastSnapshotAt.toLocaleTimeString()}
              </span>
            )}
            <span className={`pill ${sseConnected ? "pill-sse-on" : "pill-sse-off"}`}>
              SSE {sseConnected ? "●" : "○"}
            </span>
          </div>

          <div className="daedalus-header__physiology cin-arrive">
            <div className="cin-arrive cin-arrive-stagger-1">
              <EmbodimentAvatar
                posture={scene.posture}
                arousal={scene.motion}
                stability={orchestration.affect.stability}
                microMotion={dominantSignal?.avatarMicroMotion}
              />
            </div>
            <div className="cin-arrive cin-arrive-stagger-2">
              <AttentionHalo
                intensity={scene.glow}
                focus={orchestration.affect.focus}
                colorShift={dominantSignal?.haloColorShift ?? 0}
              />
            </div>
            <div className="cin-arrive cin-arrive-stagger-3">
              <CockpitOverlay
                attentionLevel={expressive.attention.level}
                guidanceCue={dominantSignal?.guidanceCue ?? "none"}
                continuityLabel={continuityLabel}
              />
            </div>
            <span className={`pill pill-intent pill-intent--${orchestration.intent} cin-arrive cin-arrive-stagger-3`}>
              {orchestration.intent}
            </span>
            {scene.continuityBadge && (
              <span className={`conductor-badge conductor-badge--${scene.continuityBadge.kind} cin-arrive cin-arrive-stagger-3`}>
                {scene.continuityBadge.label}
              </span>
            )}
          </div>

          <KernelThrone throne={throne} connectivity={connectivity} epistemic={epistemic} operator={operatorCtx} embodied={embodied} nodePresence={nodePresence} attentionTask={attentionTask} continuity={sysContinuity} preSeal={preSeal} onRollback={kernelRollback} />
          <KernelRite throne={throne} />

          {surfaceProps.narrativeLine && (
            <div className={`narrative-whisper narrative-whisper--${surfaceProps.ribbonTone}`}>
              {surfaceProps.narrativeLine}
            </div>
          )}

          <AffectStrip affect={affect} onPin={pin} onUnpin={unpin} />
        </div>

        <ContinuityRibbon signals={continuitySignals} />

        <div className="cockpit-tabs">
          <button
            className={activePanel === "topology" ? "is-active" : ""}
            onClick={() => setActivePanel("topology")}
          >
            Topology
          </button>
          <button
            className={activePanel === "field" ? "is-active" : ""}
            onClick={() => setActivePanel("field")}
          >
            Field
          </button>
          <button
            className={activePanel === "governance" ? "is-active" : ""}
            onClick={() => setActivePanel("governance")}
          >
            Governance
          </button>
          <button
            className={activePanel === "beings" ? "is-active" : ""}
            onClick={() => setActivePanel("beings")}
          >
            Beings
          </button>
        </div>

        <div key={activePanel} className="cin-gaze-enter">
          {activePanel === "topology" && (
            <div className="daedalus-layout">
              <section className="daedalus-section beings-section">
                <h3>Beings</h3>
                {snapshot?.beings?.length ? (
                  <ul className="beings-list">
                    {snapshot.beings.map((b) => (
                      <li key={b.id} className="being-item">
                        <div className="being-label">{b.label}</div>
                        <div className="being-meta">
                          <span>Glow: {b.dominantGlow}</span>
                          <span>Risk: {b.dominantRisk}</span>
                          <span>Nodes: {b.nodes.length}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty">No beings in snapshot.</p>
                )}
              </section>

              <section className="daedalus-section nodes-section">
                <NodeCapabilitiesPanel
                  nodes={nodes}
                  highlightNodeId={highlightNodeId}
                  onCapabilityClick={selectCapability}
                  onNegotiationApplied={reload}
                />
              </section>
            </div>
          )}

          {activePanel === "field" && <ExpressiveFieldView nodes={nodes} />}

          {activePanel === "governance" && <GovernancePanel />}

          {activePanel === "beings" && <BeingPresencePanel beings={beings} />}
        </div>
      </div>

      <aside className="daedalus-trace-drawer">
        <h3>Capability Trace</h3>

        {liveLine && (
          <div className="trace-live-line">
            <span className="trace-live-dot">●</span>
            <span>{liveLine.label}</span>
            <span className="trace-live-time">
              {new Date(liveLine.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}

        {sseEvent?.beings && sseEvent.beings.length > 0 && (
          <NegotiationPreviewPanel event={sseEvent} />
        )}

        {loadingTrace && <p className="muted">Loading trace…</p>}
        {traceError && <p className="error">{traceError}</p>}
        {!loadingTrace && !selectedTrace && !traceError && (
          <p className="muted">Select a capability to see why it is on or off.</p>
        )}
        {selectedTrace && (
          <div className="trace-content">
            <div className="trace-header">
              <div>
                <div className="trace-node">Node: {selectedTrace.nodeId}</div>
                <div className="trace-cap">
                  Capability: {selectedTrace.capabilityName}
                </div>
              </div>
              <div className="trace-effective">
                Effective:{" "}
                {selectedTrace.effectiveEnabled ? "enabled" : "disabled"}
              </div>
            </div>
            <ul className="trace-steps">
              {selectedTrace.steps.map((step, idx) => (
                <li key={idx} className="trace-step">
                  <div className="trace-step-header">
                    <span className="trace-step-level">{step.level}</span>
                    <span className="trace-step-reason">{step.reason}</span>
                    <span className="trace-step-time">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="trace-step-message">{step.message}</div>
                  <div className="trace-step-source">Source: {step.sourceId}</div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {negotiationMessage && (
          <div className="negotiation-message">
            {loadingNegotiation ? "Applying…" : negotiationMessage}
          </div>
        )}

        <section className="trace-gov-section">
          <h4>Governance & Posture</h4>
          {govEvents.length === 0 && (
            <p className="muted">No recent governance events</p>
          )}
          {govEvents.slice().reverse().map((e, idx) => (
            <div key={idx} className="trace-gov-event">
              <span className={`pill pill-gov-${e.type === "POSTURE_CHANGED" ? "posture" : "gov"}`}>
                {e.type === "POSTURE_CHANGED"
                  ? e.posture
                  : e.type === "GOVERNANCE_OVERRIDE_APPLIED"
                    ? "Override"
                    : "Drift"}
              </span>
              {e.summary && <span className="trace-gov-summary">{e.summary}</span>}
              <span className="trace-gov-time">
                {new Date(e.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </section>
      </aside>

      <ExpressiveHud
        scene={scene}
        grammar={sceneGrammar}
        frameId={frame.frameId}
        persistence={persistence}
        telemetry={telemetry}
        analytics={analytics}
        adaptation={adaptation}
        autonomy={autonomy}
        intent={intent}
        strategy={strategy}
        metaStrategy={metaStrategy}
        metaGov={metaGov}
        fabricDashboard={fabricDashboard}
        fabricClearAll={fabricClearAll}
        halo={halo}
        crown={crown}
        kernelRollback={kernelRollback}
        governorDisplay={governorDisplay}
        timeline={timelineSnapshot}
        affect={affect.effective}
        governorPreset={governorPreset}
        postureNudge={postureNudge}
        onToggleGovernor={useCallback(() => setGovernorEnabled((v) => !v), [])}
        onSetPreset={setGovernorPreset}
        onNudgePosture={setPostureNudge}
      />
    </div>
  );
}

export { DaedalusOrchestratorPanel };
export default DaedalusOrchestratorPanel;
