import type { ContinuitySignal, ContinuitySignalKind } from "../shared/daedalus/continuityNarrator";
import "./ContinuityRibbon.css";

const MAX_SIGNALS = 3;

const KIND_ICONS: Record<ContinuitySignalKind, string> = {
  "recency": "↩",
  "streak": "·",
  "threshold": "★",
  "drift-recovery": "↑",
  "anchor": "⚓",
};

interface Props {
  signals: ContinuitySignal[];
}

export function ContinuityRibbon({ signals }: Props) {
  if (signals.length === 0) return null;

  const shown = signals.slice(0, MAX_SIGNALS);

  return (
    <div className="continuity-ribbon cin-arrive">
      {shown.map((s, i) => (
        <span key={`${s.beingId}-${s.kind}-${i}`} className={`ribbon-signal ribbon-signal--${s.kind}`}>
          <span className="ribbon-signal__icon">{KIND_ICONS[s.kind]}</span>
          <span className="ribbon-signal__name">{s.beingName}</span>
          <span className="ribbon-signal__label">{s.label}</span>
          {s.detail && <span className="ribbon-signal__detail">{s.detail}</span>}
        </span>
      ))}
    </div>
  );
}
