import type { ThroneView } from "../shared/daedalus/kernelThrone";
import type { ConnectivitySnapshot } from "../shared/daedalus/connectivity";
import type { EpistemicReport } from "../shared/daedalus/epistemicIntake";
import type { OperatorContextSnapshot } from "../shared/daedalus/operatorContext";
import type { EmbodiedPresenceSnapshot } from "../shared/daedalus/embodiedPresence";
import type { NodePresenceSnapshot } from "../shared/daedalus/nodePresence";
import type { AttentionTaskSnapshot } from "../shared/daedalus/attentionTask";
import type { SystemContinuitySnapshot } from "../shared/daedalus/systemContinuity";
import type { PreSealReport } from "../shared/daedalus/preSealValidation";
import "./KernelThrone.css";

interface Props {
  throne: ThroneView;
  connectivity: ConnectivitySnapshot;
  epistemic: EpistemicReport;
  operator: OperatorContextSnapshot;
  embodied: EmbodiedPresenceSnapshot;
  nodePresence: NodePresenceSnapshot;
  attentionTask: AttentionTaskSnapshot;
  continuity: SystemContinuitySnapshot;
  preSeal: PreSealReport;
  onRollback: () => void;
}

export function KernelThrone({ throne, connectivity, epistemic, operator, embodied, nodePresence, attentionTask, continuity, preSeal, onRollback }: Props) {
  const pulseDuration = throne.pulse > 0 ? `${1.8 - throne.pulse * 1.2}s` : "0s";

  return (
    <div
      className={`kernel-throne throne--${throne.symbol}`}
      style={{
        "--throne-glow": throne.glow,
        "--throne-stability": throne.stability,
        "--throne-pulse-duration": pulseDuration,
      } as React.CSSProperties}
    >
      <div className="throne-crown">
        <span className={`throne-symbol throne-symbol--${throne.symbol}`}>
          {throne.symbol}
        </span>
        <span className="throne-status">
          <span className={`throne-shell throne-shell--${throne.shellStatus}`}>
            {throne.shellStatus}
          </span>
          <span className={`throne-kernel throne-kernel--${throne.kernelStatus}`}>
            {throne.kernelStatus}
          </span>
        </span>
      </div>

      <div className="throne-diagnostics">
        <span
          className={`throne-invariants ${throne.invariantsPassed ? "throne-invariants--ok" : "throne-invariants--fail"}`}
        >
          {throne.invariantsHeld}/{throne.invariantsTotal}
        </span>
        {throne.overrideCount > 0 && (
          <span className="throne-overrides">
            {throne.overrideCount} override{throne.overrideCount !== 1 ? "s" : ""}
          </span>
        )}
        {throne.pendingCount > 0 && (
          <span className="throne-pending">
            {throne.pendingCount} pending
          </span>
        )}
        {throne.cappingApplied && (
          <span className="throne-capped">capped</span>
        )}
      </div>

      <div className="throne-embodied">
        <span
          className={`throne-posture throne-posture--${embodied.posture}`}
          title={`${embodied.beingCount} being${embodied.beingCount !== 1 ? "s" : ""}${embodied.dominantBeingId ? ` · dominant: ${embodied.dominantBeingId}` : ""}`}
        >
          {embodied.posture}
        </span>
        <span
          className="throne-embodiment"
          style={{ opacity: 0.4 + embodied.embodiment * 0.6 }}
          title={`embodiment ${embodied.embodiment.toFixed(2)} · motion ${embodied.motionGrammar.toFixed(2)}`}
        >
          {embodied.unifiedGlow.toFixed(2)}
        </span>
        {embodied.continuity < 0.8 && (
          <span className="throne-continuity-warn">
            {(embodied.continuity * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="throne-attention">
        <span
          className={`throne-att-tier throne-att-tier--${attentionTask.attentionTier}`}
          title={`attention ${attentionTask.attentionLevel.toFixed(2)} · load ${attentionTask.cognitiveLoad.toFixed(2)}${attentionTask.focusTarget ? ` · focus: ${attentionTask.focusTarget}` : ""}`}
        >
          {attentionTask.attentionTier}
        </span>
        {attentionTask.cognitiveLoad > 0.5 && (
          <span className="throne-cog-load">
            {(attentionTask.cognitiveLoad * 100).toFixed(0)}%
          </span>
        )}
        {attentionTask.activeTask && (
          <span
            className="throne-active-task"
            title={`task load ${attentionTask.taskLoad.toFixed(2)} · continuity ${(attentionTask.taskContinuity * 100).toFixed(0)}%`}
          >
            {attentionTask.activeTask}
          </span>
        )}
        {attentionTask.attentionContinuity < 0.6 && (
          <span className="throne-att-continuity-warn">
            {(attentionTask.attentionContinuity * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="throne-connectivity">
        <span className={`throne-sse ${connectivity.sseConnected ? "throne-sse--on" : "throne-sse--off"}`}>
          {connectivity.sseConnected ? "sse" : "sse off"}
        </span>
        {connectivity.totalCount > 0 && (
          <span className="throne-nodes">
            {connectivity.trustedCount}/{connectivity.totalCount}
          </span>
        )}
        {connectivity.quarantinedCount > 0 && (
          <span className="throne-quarantined">
            {connectivity.quarantinedCount} quar
          </span>
        )}
        {connectivity.pendingJoinCount > 0 && (
          <span className="throne-join-pending">
            {connectivity.pendingJoinCount} join
          </span>
        )}
        <span
          className={`throne-epistemic ${epistemic.healthy ? "throne-epistemic--ok" : "throne-epistemic--warn"}`}
          title={`quality ${epistemic.overallQuality.toFixed(2)} · trusted ${(epistemic.trustedRatio * 100).toFixed(0)}%`}
        >
          {epistemic.overallQuality.toFixed(2)}
        </span>
        <span
          className={`throne-freshness ${epistemic.freshness >= 0.7 ? "throne-freshness--fresh" : epistemic.freshness >= 0.4 ? "throne-freshness--stale" : "throne-freshness--cold"}`}
          title={`freshness ${(epistemic.freshness * 100).toFixed(0)}% — ratio of nodes with recent heartbeat`}
        >
          {(epistemic.freshness * 100).toFixed(0)}%
        </span>
        {epistemic.unverifiedWarning && (
          <span
            className="throne-unverified"
            title={`${epistemic.unverifiedCount} node${epistemic.unverifiedCount !== 1 ? "s" : ""} with unknown provenance (untrusted, no heartbeat)`}
          >
            {epistemic.unverifiedCount} unverified
          </span>
        )}
      </div>

      {nodePresence.totalCount > 0 && (
        <div className="throne-node-presence">
          {nodePresence.entries.map((entry) => (
            <span
              key={entry.id}
              className={`throne-node-pip${entry.joinRequested ? " throne-node-pip--pending" : entry.trusted ? " throne-node-pip--trusted" : ""}`}
              style={{ opacity: 0.3 + entry.glow * 0.7 }}
              title={`${entry.id}${entry.joinRequested ? ` · join requested (${entry.suggestedTrustTier})` : entry.trusted ? " · trusted" : " · untrusted"} · ${entry.capabilityRibbon || "no caps"}`}
            />
          ))}
          {nodePresence.joinPulse > 0 && (
            <span className="throne-join-pulse">
              {(nodePresence.joinPulse * 100).toFixed(0)}%
            </span>
          )}
        </div>
      )}

      <div className="throne-operator">
        <span className={`throne-op-mode throne-op-mode--${operator.mode}`}>
          {operator.mode}
        </span>
        {operator.overrideCount > 0 && (
          <span className="throne-op-overrides">
            {operator.overrideCount} ctrl
          </span>
        )}
        {operator.pendingProposals > 0 && (
          <span className="throne-op-pending">
            {operator.pendingProposals} await
          </span>
        )}
        <span
          className={`throne-sovereignty ${operator.sovereignty >= 0.8 ? "throne-sovereignty--full" : operator.sovereignty >= 0.5 ? "throne-sovereignty--partial" : "throne-sovereignty--low"}`}
          title={`sovereignty ${(operator.sovereignty * 100).toFixed(0)}% · ${operator.affect}${operator.intent ? ` · ${operator.intent}` : ""}`}
        >
          {(operator.sovereignty * 100).toFixed(0)}%
        </span>
      </div>

      <div className="throne-continuity">
        <span
          className={`throne-cont-health throne-cont-health--${continuity.health}`}
          title={`identity ${continuity.identity.toFixed(2)} · state ${continuity.state.toFixed(2)} · expressive ${continuity.expressive.toFixed(2)} · temporal ${continuity.temporal.toFixed(2)}`}
        >
          {continuity.health}
        </span>
        <span
          className="throne-cont-composite"
          style={{ opacity: 0.4 + continuity.composite * 0.6 }}
        >
          {(continuity.composite * 100).toFixed(0)}%
        </span>
        {continuity.driftSignalCount > 0 && (
          <span className="throne-cont-drift">
            {continuity.driftSignalCount} drift
          </span>
        )}
        {continuity.anchorBeingId && (
          <span className="throne-cont-anchor" title={`anchor: ${continuity.anchorBeingId}`}>
            ⚓
          </span>
        )}
      </div>

      {preSeal.checkedAt > 0 && (
        <div className="throne-pre-seal">
          <span
            className={`throne-seal-status ${preSeal.passed ? "throne-seal-status--pass" : "throne-seal-status--fail"}`}
            title={`${preSeal.integrationCount} checks · ${preSeal.blockingCount} blocking · ${preSeal.warningCount} warning`}
          >
            {preSeal.passed ? "seal ready" : `${preSeal.blockingCount} blocking`}
          </span>
          {preSeal.warningCount > 0 && (
            <span
              className="throne-seal-warn"
              title={preSeal.issues.filter((i) => !i.blocking).map((i) => i.description).join(" · ")}
            >
              {preSeal.warningCount} warn
            </span>
          )}
        </div>
      )}

      <div className="throne-meter">
        <div
          className="throne-meter-fill"
          style={{ width: `${throne.stability * 100}%` }}
        />
      </div>

      {throne.kernelStatus !== "clean" && (
        <button className="throne-rollback" onClick={onRollback}>
          Rollback
        </button>
      )}
    </div>
  );
}
