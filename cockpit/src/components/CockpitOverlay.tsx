import type { GuidanceCue } from "../shared/daedalus/contracts";
import "../styles/physiology-animations.css";

interface Props {
  attentionLevel?: string;
  guidanceCue?: GuidanceCue;
  continuityLabel?: string;
}

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function CockpitOverlay({
  attentionLevel,
  guidanceCue = "none",
  continuityLabel,
}: Props) {
  const guidanceClass =
    guidanceCue === "strong"
      ? "guidance-strong"
      : guidanceCue === "subtle"
        ? "guidance-subtle"
        : undefined;

  return (
    <div className={cn("cockpit-overlay", guidanceClass)}>
      {attentionLevel && (
        <span className="overlay-attention-pill">{attentionLevel}</span>
      )}
      {continuityLabel && (
        <span className={cn(
          "overlay-continuity-pill",
          continuityLabel === "fragile" && "pill-warn",
          continuityLabel === "stable" && "pill-ok",
        )}>
          {continuityLabel}
        </span>
      )}
    </div>
  );
}
