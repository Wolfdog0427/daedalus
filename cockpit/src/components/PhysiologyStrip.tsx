import type { ExpressiveField } from "../shared/daedalus/contracts";
import "./PhysiologyStrip.css";

interface Props {
  field: ExpressiveField;
}

function bar(value: number, label: string, variant: string) {
  return (
    <div className="phys-gauge">
      <span className="phys-gauge__label">{label}</span>
      <div className="phys-gauge__track">
        <div
          className={`phys-gauge__fill phys-gauge__fill--${variant}`}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className="phys-gauge__value">{Math.round(value * 100)}</span>
    </div>
  );
}

export function PhysiologyStrip({ field }: Props) {
  return (
    <div className={`physiology-strip posture-strip--${field.posture}`}>
      <span className={`phys-posture phys-posture--${field.posture}`}>
        {field.posture}
      </span>
      <span className={`phys-attention phys-attention--${field.attention.level}`}>
        {field.attention.level}
      </span>
      {bar(field.arousal, "Arousal", "arousal")}
      {bar(field.focus, "Focus", "focus")}
      {bar(field.stability, "Stability", "stability")}
      <span className={`phys-continuity ${field.continuity.healthy ? "phys-ok" : "phys-warn"}`}>
        {field.continuity.healthy ? "Stable" : "Drifting"}
      </span>
    </div>
  );
}
