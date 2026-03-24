import { useExpressiveField } from "../hooks/useExpressiveField";
import { BehavioralFieldOverlay } from "./BehavioralFieldOverlay";
import { PhysiologyStrip } from "./PhysiologyStrip";
import type { BeingPresenceDetail } from "../shared/daedalus/contracts";
import "./BeingPresencePanel.css";

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

interface Props {
  beings: Record<string, BeingPresenceDetail>;
}

export function BeingPresencePanel({ beings }: Props) {
  const expressive = useExpressiveField(beings);
  const field = expressive.behavioral;
  const signalMap = new Map(field.signals.map((s) => [s.beingId, s]));
  const list = Object.values(beings);

  if (list.length === 0) {
    return (
      <div className="panel being-presence-panel">
        <div className="panel-title">Being Presence</div>
        <p className="empty">No beings reporting presence.</p>
      </div>
    );
  }

  return (
    <div className="panel being-presence-panel">
      <div className="panel-title">Being Presence</div>

      <PhysiologyStrip field={expressive} />
      <BehavioralFieldOverlay field={field} />

      <div className="being-presence-grid">
        {list.map((b) => {
          const signal = signalMap.get(b.id);
          const isDominant = field.dominantBeingId === b.id;
          const motionClass = signal?.avatarMicroMotion !== "none"
            ? `motion-${signal?.avatarMicroMotion}`
            : undefined;
          const guidanceClass = signal?.guidanceCue !== "none"
            ? `guidance-${signal?.guidanceCue}`
            : undefined;

          return (
            <div
              key={b.id}
              className={cn(
                "being-card",
                `posture-${b.posture}`,
                `presence-${b.presenceMode}`,
                b.isSpeaking && "speaking",
                b.isGuiding && "guiding",
                isDominant && "being-card--dominant",
                motionClass,
                guidanceClass,
              )}
            >
              <header className="being-card__header">
                <span className="being-card__name">{b.name}</span>
                <span className={`being-card__mode badge badge-${b.presenceMode}`}>
                  {b.presenceMode}
                </span>
              </header>

              <div
                className="being-card__glow-ring"
                style={{
                  opacity: signal?.haloIntensity ?? b.glow.intensity,
                  boxShadow: `0 0 ${12 * (signal?.haloIntensity ?? b.glow.intensity)}px rgba(80,160,255,${(signal?.haloIntensity ?? b.glow.intensity) * 0.6})`,
                  filter: signal ? `hue-rotate(${signal.haloColorShift * 60}deg)` : undefined,
                }}
              />

              <div className="being-card__stats">
                <div className="being-card__stat">
                  <label>Posture</label>
                  <span>{b.posture}</span>
                </div>
                <div className="being-card__stat">
                  <label>Attention</label>
                  <span>{b.attention.level}</span>
                </div>
                <div className="being-card__stat">
                  <label>Influence</label>
                  <span>{Math.round(b.influenceLevel * 100)}%</span>
                </div>
                <div className="being-card__stat">
                  <label>Glow</label>
                  <span>{b.glow.level}</span>
                </div>
              </div>

              <div className="being-card__flags">
                {b.isSpeaking && <span className="being-card__flag flag-speaking">Speaking</span>}
                {b.isGuiding && <span className="being-card__flag flag-guiding">Guiding</span>}
                {b.autopilot.enabled && (
                  <span className="being-card__flag flag-autopilot">
                    Autopilot ({b.autopilot.scope})
                  </span>
                )}
                {signal?.avatarMicroMotion !== "none" && (
                  <span className="being-card__flag flag-motion">
                    {signal?.avatarMicroMotion}
                  </span>
                )}
              </div>

              <div className="being-card__continuity">
                <span className={b.continuity.healthy ? "continuity-ok" : "continuity-warn"}>
                  {b.continuity.healthy ? "Healthy" : "Drifting"}
                </span>
                <span className="continuity-streak">Streak: {b.continuity.streak}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
