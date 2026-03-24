import type { ThroneView } from "../shared/daedalus/kernelThrone";
import "./KernelRite.css";

interface Props {
  throne: ThroneView;
}

/**
 * The Kernel Rite — a purely ceremonial visual that acknowledges
 * the Kernel's sovereign presence. Driven entirely by the ThroneView;
 * zero feedback, zero governance effect, zero autonomy.
 */
export function KernelRite({ throne }: Props) {
  const glowOpacity = 0.4 + throne.glow * 0.6;
  const pulseScale = 1 + throne.pulse * 0.12;
  const ringBorder = throne.invariantsPassed
    ? "rgba(255,255,255,0.15)"
    : "rgba(248,81,73,0.25)";

  return (
    <div className={`kernel-rite rite--${throne.symbol}`}>
      <div
        className={`rite-crown rite-crown--${throne.symbol}`}
        style={{ opacity: glowOpacity, transform: `scale(${pulseScale})` }}
      >
        {throne.symbol}
      </div>

      <div className="rite-ring" style={{ borderColor: ringBorder }}>
        <div
          className="rite-halo"
          style={{ opacity: 0.3 + throne.stability * 0.5 }}
        />
      </div>

      <div className="rite-caption">
        <span className="rite-title">the kernel is throned</span>
        <span className="rite-subtitle">
          {throne.shellStatus} · {throne.kernelStatus}
        </span>
      </div>
    </div>
  );
}
