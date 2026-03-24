import type { DaedalusEventPayload } from "../hooks/useDaedalusEvents";
import "./NegotiationPreviewPanel.css";

interface Props {
  event?: DaedalusEventPayload | null;
}

export function NegotiationPreviewPanel({ event }: Props) {
  if (!event?.beings || event.beings.length === 0) return null;

  return (
    <div className="panel negotiation-preview-panel">
      <div className="panel-title">Negotiation Preview</div>
      {event.beings.map((b: any) => (
        <div key={b.being.id} className="neg-vote-row">
          <span className="neg-being-label">{b.being.label}</span>
          <span className={`badge badge-${b.vote.toLowerCase()}`}>{b.vote}</span>
          <span className="neg-weight">{Math.round(b.weight * 100)}%</span>
        </div>
      ))}
      {event.summary && <div className="neg-summary">{event.summary}</div>}
    </div>
  );
}
