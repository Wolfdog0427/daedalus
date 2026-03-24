import { useState, useEffect, useCallback } from "react";
import { fetchAlignmentConfig, saveAlignmentConfig, type AlignmentConfig } from "../api/daedalusClient";
import "./AlignmentControls.css";

const FIELD_META: { key: keyof AlignmentConfig; label: string; step: number; min: number; max: number }[] = [
  { key: "sovereigntyWeight", label: "Sovereignty Weight", step: 0.05, min: 0, max: 1 },
  { key: "identityWeight", label: "Identity Weight", step: 0.05, min: 0, max: 1 },
  { key: "governanceWeight", label: "Governance Weight", step: 0.05, min: 0, max: 1 },
  { key: "stabilityWeight", label: "Stability Weight", step: 0.05, min: 0, max: 1 },
  { key: "alignmentFloor", label: "Alignment Floor", step: 1, min: 0, max: 100 },
];

export function AlignmentControls() {
  const [config, setConfig] = useState<AlignmentConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchAlignmentConfig();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load config");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (!config) {
    return (
      <section className="alignment-controls">
        <h3 className="alignment-controls__title">Alignment Controls</h3>
        {error
          ? <p className="alignment-controls__error">{error}</p>
          : <p className="alignment-controls__muted">Loading alignment config...</p>}
      </section>
    );
  }

  const updateField = (key: keyof AlignmentConfig, value: number) => {
    setConfig(prev => prev ? { ...prev, [key]: value } : prev);
    setSuccess(false);
  };

  const save = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const saved = await saveAlignmentConfig(config);
      setConfig(saved);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const weightSum = config.sovereigntyWeight + config.identityWeight +
    config.governanceWeight + config.stabilityWeight;
  const weightsValid = Math.abs(weightSum - 1.0) < 0.01;

  return (
    <section className="alignment-controls">
      <h3 className="alignment-controls__title">Alignment Controls</h3>

      <div className="alignment-controls__fields">
        {FIELD_META.map(({ key, label, step, min, max }) => (
          <label key={key} className="alignment-controls__field">
            <span className="alignment-controls__label">{label}</span>
            <input
              className="alignment-controls__input"
              type="number"
              step={step}
              min={min}
              max={max}
              value={config[key]}
              onChange={e => {
                const v = parseFloat(e.target.value);
                updateField(key, Number.isFinite(v) ? v : 0);
              }}
            />
          </label>
        ))}
      </div>

      {!weightsValid && (
        <p className="alignment-controls__warning">
          Weights sum to {weightSum.toFixed(2)} (should be 1.00)
        </p>
      )}

      <div className="alignment-controls__actions">
        <button
          className="alignment-controls__save"
          onClick={save}
          disabled={saving}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        {success && <span className="alignment-controls__success">Saved</span>}
        {error && <span className="alignment-controls__error">{error}</span>}
      </div>
    </section>
  );
}
