import { useState, useCallback } from "react";
import type { NodeInfo } from "./NodeCapabilitiesPanel";
import { useDaedalusEvents } from "../hooks/useDaedalusEvents";
import type { DaedalusEventPayload } from "../hooks/useDaedalusEvents";
import "./ExpressiveFieldView.css";

const GLOW_RADIUS: Record<string, number> = {
  none: 0,
  low: 4,
  medium: 8,
  high: 14,
};

const RISK_RED: Record<string, number> = {
  low: 40,
  medium: 120,
  high: 200,
};

interface Props {
  nodes?: NodeInfo[];
}

export function ExpressiveFieldView({ nodes = [] }: Props) {
  const [pulseNodeId, setPulseNodeId] = useState<string | null>(null);

  useDaedalusEvents(useCallback((event: DaedalusEventPayload) => {
    if (
      (event.type === "NODE_GLOW_UPDATED" || event.type === "NODE_RISK_UPDATED") &&
      event.nodeId
    ) {
      setPulseNodeId(event.nodeId);
      setTimeout(() => setPulseNodeId(null), 350);
    }
  }, []));

  if (nodes.length === 0) return <div className="empty">No nodes to visualize</div>;

  const cols = Math.min(nodes.length, 6);
  const w = 100 + cols * 120;
  const rows = Math.ceil(nodes.length / cols);
  const h = 80 + rows * 120;

  return (
    <div className="panel expressive-field">
      <div className="panel-title">Expressive Field</div>
      <svg width={w} height={h} className="field-svg">
        {nodes.map((n, i) => {
          const col = i % cols;
          const row = Math.floor(i / cols);
          const x = 70 + col * 120;
          const y = 50 + row * 120;
          const glowR = 25 + (GLOW_RADIUS[n.glow] ?? 0);
          const riskR = RISK_RED[n.risk] ?? 40;
          const isPulsing = pulseNodeId === n.id;

          return (
            <g key={n.id} className={isPulsing ? "field-node--pulse" : ""}>
              <circle
                cx={x}
                cy={y}
                r={glowR + (isPulsing ? 6 : 0)}
                className="field-glow"
                fill={`rgba(80,160,255,${0.08 + (GLOW_RADIUS[n.glow] ?? 0) * 0.03})`}
              />
              <circle
                cx={x}
                cy={y}
                r={18}
                className={`field-risk field-risk--${n.risk}`}
                fill={`rgba(${riskR},0,0,0.6)`}
              />
              <text x={x} y={y + glowR + 14} textAnchor="middle" className="field-label">
                {n.id}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
