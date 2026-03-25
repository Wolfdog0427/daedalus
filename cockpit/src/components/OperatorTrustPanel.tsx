import { useState, useEffect, useCallback } from "react";
import {
  fetchOperatorTrust,
  bindOperatorProfile,
  unbindOperator,
  enableFreeze,
  disableFreeze,
  type OperatorTrustCockpitSnapshot,
  type OperatorTrustPosture,
} from "../api/daedalusClient";
import "./OperatorTrustPanel.css";

const POSTURE_LABELS: Record<OperatorTrustPosture, string> = {
  unbound: "Unbound",
  trusted_canonical: "Trusted (Canonical)",
  trusted_uncalibrated: "Trusted (Uncalibrated)",
  cautious: "Cautious",
  hostile_or_unknown: "Hostile / Unknown",
};

const POSTURE_COLORS: Record<OperatorTrustPosture, string> = {
  unbound: "#8b949e",
  trusted_canonical: "#4caf50",
  trusted_uncalibrated: "#66bb6a",
  cautious: "#ffb300",
  hostile_or_unknown: "#f85149",
};

function TrustBar({ label, value }: { label: string; value: number }) {
  const color =
    value >= 80 ? "#4caf50" :
    value >= 50 ? "#ffb300" :
    "#f85149";
  return (
    <div className="trust-bar">
      <span className="trust-bar__label">{label}</span>
      <div className="trust-bar__track">
        <div className="trust-bar__fill" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="trust-bar__value">{Math.round(value)}</span>
    </div>
  );
}

type BindStep = "idle" | "form" | "confirm" | "binding" | "done";

function BindRitual({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<BindStep>("idle");
  const [id, setId] = useState("spencer");
  const [displayName, setDisplayName] = useState("Spencer");
  const [error, setError] = useState<string | null>(null);

  const handleBind = useCallback(async () => {
    setStep("binding");
    setError(null);
    try {
      await bindOperatorProfile({
        id,
        displayName,
        values: {
          operatorSovereignty: true,
          noSilentRepoShifts: true,
          explicitNotification: true,
          constitutionalGovernance: true,
          longHorizonStability: true,
        },
        continuityAnchors: ["activation skeleton", "constitutional governance", "alignment pipeline"],
        risk: {
          allowExperimentalNodes: true,
          allowAutoApproval: true,
          preferSafetyOverConvenience: true,
        },
      });
      setStep("done");
      setTimeout(onComplete, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Binding failed");
      setStep("confirm");
    }
  }, [id, displayName, onComplete]);

  if (step === "idle") {
    return (
      <div className="bind-ritual">
        <div className="bind-ritual__prompt">
          <span className="bind-ritual__icon">{"\u2666"}</span>
          <div className="bind-ritual__prompt-text">
            <strong>No operator is bound.</strong>
            <span>Daedalus requires an operator identity to enable trust calibration and high-risk action gating.</span>
          </div>
        </div>
        <button className="bind-ritual__btn bind-ritual__btn--primary" onClick={() => setStep("form")}>
          Begin Binding Ritual
        </button>
      </div>
    );
  }

  if (step === "form") {
    return (
      <div className="bind-ritual">
        <h4 className="bind-ritual__step-title">Step 1 — Identify Yourself</h4>
        <p className="bind-ritual__step-desc">
          Provide your canonical operator identity. This binds Daedalus to you as the sovereign operator.
        </p>
        <div className="bind-ritual__field">
          <label className="bind-ritual__label">Operator ID</label>
          <input
            className="bind-ritual__input"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="e.g. spencer"
          />
        </div>
        <div className="bind-ritual__field">
          <label className="bind-ritual__label">Display Name</label>
          <input
            className="bind-ritual__input"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Spencer"
          />
        </div>
        <div className="bind-ritual__actions">
          <button className="bind-ritual__btn bind-ritual__btn--secondary" onClick={() => setStep("idle")}>Cancel</button>
          <button
            className="bind-ritual__btn bind-ritual__btn--primary"
            onClick={() => setStep("confirm")}
            disabled={!id.trim() || !displayName.trim()}
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (step === "confirm") {
    return (
      <div className="bind-ritual">
        <h4 className="bind-ritual__step-title">Step 2 — Confirm Binding</h4>
        <p className="bind-ritual__step-desc">
          You are about to bind Daedalus to operator <strong>{displayName}</strong> ({id}).
          This enables trust calibration, high-risk gating, and constitutional governance under your authority.
        </p>
        <div className="bind-ritual__confirm-box">
          <div className="bind-ritual__confirm-row"><span>Operator ID:</span><strong>{id}</strong></div>
          <div className="bind-ritual__confirm-row"><span>Display Name:</span><strong>{displayName}</strong></div>
          <div className="bind-ritual__confirm-row"><span>Sovereignty:</span><strong>Enabled</strong></div>
          <div className="bind-ritual__confirm-row"><span>Constitutional Governance:</span><strong>Enabled</strong></div>
          <div className="bind-ritual__confirm-row"><span>Long-Horizon Stability:</span><strong>Enabled</strong></div>
        </div>
        {error && <p className="bind-ritual__error">{error}</p>}
        <div className="bind-ritual__actions">
          <button className="bind-ritual__btn bind-ritual__btn--secondary" onClick={() => setStep("form")}>Back</button>
          <button className="bind-ritual__btn bind-ritual__btn--primary" onClick={handleBind}>
            Confirm &amp; Bind
          </button>
        </div>
      </div>
    );
  }

  if (step === "binding") {
    return (
      <div className="bind-ritual">
        <div className="bind-ritual__progress">
          <span className="bind-ritual__spinner" />
          <span>Binding operator identity...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bind-ritual">
      <div className="bind-ritual__success">
        <span className="bind-ritual__success-icon">{"\u2713"}</span>
        <span>Operator <strong>{displayName}</strong> bound successfully.</span>
      </div>
    </div>
  );
}

export function OperatorTrustPanel() {
  const [data, setData] = useState<OperatorTrustCockpitSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unbinding, setUnbinding] = useState(false);
  const [freezeLoading, setFreezeLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const snap = await fetchOperatorTrust();
      setData(snap);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load operator trust");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 5_000);
    return () => clearInterval(id);
  }, [load]);

  const handleUnbind = useCallback(async () => {
    if (!confirm("Unbind the current operator? All high-risk actions will be disabled until a new operator binds.")) return;
    setUnbinding(true);
    try {
      await unbindOperator();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbind failed");
    } finally {
      setUnbinding(false);
    }
  }, [load]);

  const handleToggleFreeze = useCallback(async () => {
    if (!data) return;
    setFreezeLoading(true);
    try {
      if (data.freeze.frozen) {
        await disableFreeze();
      } else {
        const reason = prompt("Freeze reason:", "Manual operator freeze");
        if (!reason) { setFreezeLoading(false); return; }
        await enableFreeze(reason);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Freeze toggle failed");
    } finally {
      setFreezeLoading(false);
    }
  }, [data, load]);

  const isBound = data && data.boundOperatorId;

  return (
    <section className="operator-trust-panel">
      <h3 className="operator-trust-panel__title">Operator Identity</h3>

      {error && <p className="operator-trust-panel__error">{error}</p>}

      {data && !isBound && <BindRitual onComplete={load} />}

      {data && isBound && (
        <>
          <div className="operator-trust-panel__header">
            <div className="operator-trust-panel__operator">
              <span className="operator-trust-panel__name">{data.boundOperatorName ?? data.boundOperatorId}</span>
              <span className="operator-trust-panel__id">({data.boundOperatorId})</span>
            </div>
            <div
              className="operator-trust-panel__posture-badge"
              style={{ background: POSTURE_COLORS[data.posture] + "22", color: POSTURE_COLORS[data.posture], borderColor: POSTURE_COLORS[data.posture] + "44" }}
            >
              {POSTURE_LABELS[data.posture]}
            </div>
          </div>

          <div className="operator-trust-panel__score-row">
            <div className="operator-trust-panel__score-ring" style={{ borderColor: POSTURE_COLORS[data.posture] }}>
              <span className="operator-trust-panel__score-number">{data.trustScore}</span>
            </div>
            <div className="operator-trust-panel__score-meta">
              <span className="operator-trust-panel__comfort">{data.comfortPosture === "fluid" ? "Fluid UX" : data.comfortPosture === "careful" ? "Careful UX" : "Normal UX"}</span>
              <span className="operator-trust-panel__calibrated">{data.calibrated ? "Calibrated" : "Not calibrated"}</span>
            </div>
          </div>

          <p className="operator-trust-panel__narrative">{data.narrative}</p>

          <div className="operator-trust-panel__axes">
            <TrustBar label="Credentials" value={data.axes.credentials} />
            <TrustBar label="Device" value={data.axes.deviceGraph} />
            <TrustBar label="Behavior" value={data.axes.behaviorProfile} />
            <TrustBar label="Continuity" value={data.axes.continuity} />
          </div>

          {data.freeze.frozen && (
            <div className="operator-trust-panel__freeze">
              Constitutional Freeze Active: {data.freeze.reason}
            </div>
          )}

          <div className="operator-trust-panel__control-row">
            <button
              className="operator-trust-panel__ctrl-btn operator-trust-panel__ctrl-btn--freeze"
              onClick={handleToggleFreeze}
              disabled={freezeLoading}
            >
              {freezeLoading ? "..." : data.freeze.frozen ? "Unfreeze Constitution" : "Freeze Constitution"}
            </button>
            <button
              className="operator-trust-panel__ctrl-btn operator-trust-panel__ctrl-btn--unbind"
              onClick={handleUnbind}
              disabled={unbinding}
            >
              {unbinding ? "Unbinding..." : "Unbind Operator"}
            </button>
          </div>

          {data.recentHighRiskDecisions.length > 0 && (
            <div className="operator-trust-panel__hr-section">
              <h4>Recent High-Risk Decisions</h4>
              {data.recentHighRiskDecisions.slice().reverse().slice(0, 5).map((d, i) => (
                <div key={i} className={`operator-trust-panel__hr-entry ${d.allowed ? "hr--allowed" : "hr--denied"}`}>
                  <span className="hr__action">{d.action}</span>
                  <span className={`hr__badge ${d.allowed ? "hr__badge--allowed" : "hr__badge--denied"}`}>
                    {d.allowed ? "ALLOWED" : "DENIED"}
                  </span>
                  {d.reasons.length > 0 && <span className="hr__reasons">{d.reasons.join(", ")}</span>}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!data && !error && <p className="operator-trust-panel__muted">Loading...</p>}
    </section>
  );
}
