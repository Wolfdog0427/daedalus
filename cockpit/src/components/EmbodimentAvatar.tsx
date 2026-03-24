import type { DaedalusPosture, AvatarMicroMotion } from "../shared/daedalus/contracts";
import "../styles/physiology-animations.css";

interface Props {
  posture?: DaedalusPosture;
  arousal?: number;
  stability?: number;
  microMotion?: AvatarMicroMotion;
}

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function EmbodimentAvatar({
  posture,
  arousal = 0,
  stability = 1,
  microMotion = "none",
}: Props) {
  const motionClass =
    microMotion === "tilt"
      ? "avatar-motion-tilt"
      : microMotion === "lean"
        ? "avatar-motion-lean"
        : microMotion === "pulse"
          ? "avatar-motion-pulse"
          : undefined;

  const breathingClass =
    arousal > 0.7
      ? "avatar-breath-fast"
      : arousal > 0.3
        ? "avatar-breath"
        : undefined;

  const stabilityClass =
    stability < 0.4
      ? "avatar-unstable"
      : stability < 0.8
        ? "avatar-soft"
        : undefined;

  const glowRadius = 18 + Math.round(arousal * 12);
  const glowOpacity = 0.15 + arousal * 0.25;

  return (
    <div
      className={cn(
        "embodiment-avatar",
        posture && `posture-${posture}`,
        motionClass,
        breathingClass,
        stabilityClass,
      )}
    >
      <svg width="48" height="48" viewBox="0 0 48 48" className="avatar-svg">
        <circle
          cx="24" cy="24" r={glowRadius}
          fill={`rgba(80,160,255,${glowOpacity})`}
          className="avatar-aura"
        />
        <circle cx="24" cy="24" r="14" className="avatar-core" />
      </svg>
    </div>
  );
}
