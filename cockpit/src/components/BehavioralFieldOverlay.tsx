import type { BehavioralField } from "../shared/daedalus/contracts";
import "./BehavioralFieldOverlay.css";

interface Props {
  field: BehavioralField;
}

export function BehavioralFieldOverlay({ field }: Props) {
  if (!field.dominantBeingId || field.signals.length === 0) return null;

  const dominant = field.signals.find(
    (s) => s.beingId === field.dominantBeingId,
  );
  if (!dominant) return null;

  const haloStyle = {
    opacity: dominant.haloIntensity,
    filter: `hue-rotate(${dominant.haloColorShift * 60}deg)`,
  };

  return (
    <div className="behavioral-field-overlay">
      <div className="bfo-halo" style={haloStyle} />
      <div className="bfo-readout">
        <span className="bfo-dominant">
          Dominant: <strong>{dominant.beingId}</strong>
        </span>
        <span className={`bfo-motion bfo-motion--${dominant.avatarMicroMotion}`}>
          {dominant.avatarMicroMotion !== "none" && dominant.avatarMicroMotion}
        </span>
        <span className={`bfo-guidance bfo-guidance--${dominant.guidanceCue}`}>
          {dominant.guidanceCue !== "none" && `${dominant.guidanceCue} guidance`}
        </span>
      </div>
      <div className="bfo-signals">
        {field.signals.map((s) => (
          <div
            key={s.beingId}
            className={`bfo-signal ${s.beingId === field.dominantBeingId ? "bfo-signal--dominant" : ""}`}
          >
            <span className="bfo-signal__id">{s.beingId}</span>
            <div className="bfo-signal__bar-track">
              <div
                className="bfo-signal__bar-fill"
                style={{ width: `${s.influenceWeight * 100}%`, opacity: s.haloIntensity }}
              />
            </div>
            <span className="bfo-signal__pct">{Math.round(s.influenceWeight * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
