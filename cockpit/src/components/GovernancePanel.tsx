import { useEffect, useState, useCallback, type CSSProperties, type FormEvent } from "react";
import {
  fetchOverrides,
  fetchDrifts,
  createOverride,
  clearOverrides,
  clearDrifts,
} from "../api/daedalusClient";
import { useDaedalusEvents } from "../hooks/useDaedalusEvents";
import type { GovernanceOverride, ContinuityDrift } from "../shared/daedalus/contracts";
import "./GovernancePanel.css";

const formShell: CSSProperties = {
  background: "#1a1a2e",
  color: "white",
  border: "1px solid #333",
  borderRadius: 6,
  padding: "12px 14px",
  marginBottom: 16,
};

const labelStyle: CSSProperties = { display: "block", fontSize: 12, marginBottom: 4, opacity: 0.9 };

const inputStyle: CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  background: "#12121f",
  color: "white",
  border: "1px solid #333",
  borderRadius: 4,
  padding: "6px 8px",
  marginBottom: 10,
};

const selectStyle: CSSProperties = { ...inputStyle, cursor: "pointer" };

const btnStyle: CSSProperties = {
  background: "#2a2a44",
  color: "white",
  border: "1px solid #333",
  borderRadius: 4,
  padding: "8px 14px",
  cursor: "pointer",
  marginRight: 8,
  marginTop: 4,
};

const btnDangerStyle: CSSProperties = { ...btnStyle, background: "#3d2228" };

export function GovernancePanel() {
  const [overrides, setOverrides] = useState<GovernanceOverride[]>([]);
  const [drifts, setDrifts] = useState<ContinuityDrift[]>([]);
  const [error, setError] = useState<string>();
  const [reason, setReason] = useState("");
  const [scope, setScope] = useState<"NODE" | "CAPABILITY" | "GLOBAL">("GLOBAL");
  const [effect, setEffect] = useState<"ALLOW" | "DENY" | "ESCALATE">("ALLOW");
  const [formBusy, setFormBusy] = useState(false);

  const loadOverrides = useCallback(() => {
    fetchOverrides().then(setOverrides).catch((e) => setError(e.message));
  }, []);

  const loadDrifts = useCallback(() => {
    fetchDrifts().then(setDrifts).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadOverrides();
    loadDrifts();
  }, [loadOverrides, loadDrifts]);

  useDaedalusEvents((event) => {
    if (event.type === "GOVERNANCE_OVERRIDE_APPLIED") loadOverrides();
    if (event.type === "CONTINUITY_DRIFT_DETECTED") loadDrifts();
  });

  const onCreateOverride = async (e: FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Reason is required");
      return;
    }
    setError(undefined);
    setFormBusy(true);
    try {
      await createOverride({
        createdBy: { id: "cockpit-ui", role: "operator", label: "Cockpit" },
        reason: reason.trim(),
        scope,
        effect,
      });
      setReason("");
      loadOverrides();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setFormBusy(false);
    }
  };

  const onClearOverrides = async () => {
    setError(undefined);
    setFormBusy(true);
    try {
      await clearOverrides();
      loadOverrides();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setFormBusy(false);
    }
  };

  const onClearDrifts = async () => {
    setError(undefined);
    setFormBusy(true);
    try {
      await clearDrifts();
      loadDrifts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setFormBusy(false);
    }
  };

  return (
    <div className="panel governance-panel">
      <div className="panel-title">Governance</div>
      {error && <div className="error-msg">{error}</div>}

      <div style={formShell}>
        <form onSubmit={onCreateOverride}>
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Create Override</div>
          <label style={labelStyle} htmlFor="gov-reason">
            Reason
          </label>
          <input
            id="gov-reason"
            type="text"
            value={reason}
            onChange={(ev) => setReason(ev.target.value)}
            style={inputStyle}
            placeholder="Why this override"
            disabled={formBusy}
          />
          <label style={labelStyle} htmlFor="gov-scope">
            Scope
          </label>
          <select
            id="gov-scope"
            value={scope}
            onChange={(ev) => setScope(ev.target.value as typeof scope)}
            style={selectStyle}
            disabled={formBusy}
          >
            <option value="NODE">NODE</option>
            <option value="CAPABILITY">CAPABILITY</option>
            <option value="GLOBAL">GLOBAL</option>
          </select>
          <label style={labelStyle} htmlFor="gov-effect">
            Effect
          </label>
          <select
            id="gov-effect"
            value={effect}
            onChange={(ev) => setEffect(ev.target.value as typeof effect)}
            style={selectStyle}
            disabled={formBusy}
          >
            <option value="ALLOW">ALLOW</option>
            <option value="DENY">DENY</option>
            <option value="ESCALATE">ESCALATE</option>
          </select>
          <button type="submit" style={btnStyle} disabled={formBusy}>
            {formBusy ? "…" : "Submit override"}
          </button>
        </form>
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #333" }}>
          <button type="button" style={btnDangerStyle} disabled={formBusy} onClick={onClearOverrides}>
            Clear All Overrides
          </button>
          <button type="button" style={btnDangerStyle} disabled={formBusy} onClick={onClearDrifts}>
            Clear All Drifts
          </button>
        </div>
      </div>

      <h4>Overrides</h4>
      {overrides.length === 0 && <p className="empty">No active overrides</p>}
      {overrides.map((o) => (
        <div key={o.id} className="gov-row">
          <span className={`badge badge-${o.effect.toLowerCase()}`}>{o.effect}</span>
          <span className="gov-scope">{o.scope}</span>
          <span className="gov-reason">{o.reason}</span>
          <span className="gov-by">{o.createdBy?.label}</span>
        </div>
      ))}

      <h4>Continuity Drifts</h4>
      {drifts.length === 0 && <p className="empty">No drifts detected</p>}
      {drifts.map((d) => (
        <div key={d.id} className="gov-row">
          <span className={`badge badge-drift-${d.severity.toLowerCase()}`}>{d.severity}</span>
          <span className="gov-reason">{d.summary}</span>
          <span className="gov-time">{new Date(d.detectedAt).toLocaleTimeString()}</span>
        </div>
      ))}
    </div>
  );
}
