import type { OperatorAffect, OperatorAffectState } from "../shared/daedalus/operatorAffect";
import "../styles/operator-affect.css";

const STATES: OperatorAffectState[] = ["settled", "focused", "exploratory", "under-load"];

interface Props {
  affect: OperatorAffect;
  onPin: (state: OperatorAffectState) => void;
  onUnpin: () => void;
}

export function AffectStrip({ affect, onPin, onUnpin }: Props) {
  return (
    <div className="affect-strip">
      {STATES.map((s) => (
        <button
          key={s}
          className={[
            "affect-strip__state",
            affect.effective === s && "is-active",
            affect.pinned === s && "is-pinned",
          ].filter(Boolean).join(" ")}
          onClick={() => affect.pinned === s ? onUnpin() : onPin(s)}
          title={
            affect.pinned === s
              ? `Unpin ${s}`
              : affect.suggested === s
                ? `${s} (suggested) — click to pin`
                : `Pin ${s}`
          }
        >
          {s}
        </button>
      ))}
      {affect.pinned && (
        <button className="affect-strip__unpin" onClick={onUnpin} title="Clear pin">
          unpin
        </button>
      )}
    </div>
  );
}
