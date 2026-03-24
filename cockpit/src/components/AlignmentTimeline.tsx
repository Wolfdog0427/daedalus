import "./AlignmentTimeline.css";

interface AlignmentTimelineProps {
  history: Array<{
    timestamp: number;
    alignment: number;
  }>;
  height?: number;
}

function segmentColor(alignment: number): string {
  if (alignment >= 85) return "#3fb950";
  if (alignment >= 70) return "#58a6ff";
  if (alignment >= 55) return "#d29922";
  if (alignment >= 40) return "#f0883e";
  return "#f85149";
}

export function AlignmentTimeline({ history, height = 32 }: AlignmentTimelineProps) {
  if (!history || history.length < 2) {
    return (
      <div className="alignment-timeline alignment-timeline--empty">
        <span className="alignment-timeline__placeholder">
          {history?.length === 1 ? "Waiting for data..." : "No alignment data"}
        </span>
      </div>
    );
  }

  const viewWidth = 200;
  const viewHeight = height;
  const maxAlignment = 100;

  const points = history.map((h, idx) => ({
    x: (idx / (history.length - 1)) * viewWidth,
    y: viewHeight - (h.alignment / maxAlignment) * viewHeight,
    alignment: h.alignment,
  }));

  const areaPath = [
    `M ${points[0].x} ${viewHeight}`,
    `L ${points[0].x} ${points[0].y}`,
    ...points.slice(1).map(p => `L ${p.x} ${p.y}`),
    `L ${points[points.length - 1].x} ${viewHeight}`,
    "Z",
  ].join(" ");

  const thresholdY80 = viewHeight - (80 / maxAlignment) * viewHeight;
  const thresholdY60 = viewHeight - (60 / maxAlignment) * viewHeight;

  return (
    <div className="alignment-timeline">
      <div className="alignment-timeline__label">Alignment Trend</div>
      <svg
        className="alignment-timeline__svg"
        viewBox={`0 0 ${viewWidth} ${viewHeight}`}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="timeline-fill-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(88, 166, 255, 0.25)" />
            <stop offset="100%" stopColor="rgba(88, 166, 255, 0.02)" />
          </linearGradient>
        </defs>

        <path d={areaPath} fill="url(#timeline-fill-grad)" />

        <line
          x1="0" y1={thresholdY80}
          x2={viewWidth} y2={thresholdY80}
          stroke="rgba(63, 185, 80, 0.2)"
          strokeWidth="0.5"
          strokeDasharray="4 2"
        />
        <line
          x1="0" y1={thresholdY60}
          x2={viewWidth} y2={thresholdY60}
          stroke="rgba(248, 81, 73, 0.2)"
          strokeWidth="0.5"
          strokeDasharray="4 2"
        />

        {points.map((point, idx) => {
          if (idx === 0) return null;
          const prev = points[idx - 1];
          return (
            <line
              key={idx}
              x1={prev.x} y1={prev.y}
              x2={point.x} y2={point.y}
              stroke={segmentColor(point.alignment)}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          );
        })}

        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r="2"
            fill={segmentColor(points[points.length - 1].alignment)}
          />
        )}
      </svg>
    </div>
  );
}
