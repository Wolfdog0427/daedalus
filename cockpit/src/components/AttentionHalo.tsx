import "../styles/physiology-animations.css";

interface Props {
  intensity?: number;
  focus?: number;
  colorShift?: number;
}

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function AttentionHalo({
  intensity = 0,
  focus = 0,
  colorShift = 0,
}: Props) {
  const clamped = Math.max(0, Math.min(1, intensity));
  const clampedFocus = Math.max(0, Math.min(1, focus));

  const focusClass =
    clampedFocus > 0.7
      ? "halo-focus-strong"
      : clampedFocus > 0.3
        ? "halo-focus"
        : undefined;

  return (
    <div
      className={cn("attention-halo", focusClass)}
      style={{
        opacity: clamped,
        filter: `hue-rotate(${colorShift * 40}deg)`,
      }}
    />
  );
}
