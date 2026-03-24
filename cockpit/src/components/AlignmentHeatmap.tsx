import "./AlignmentHeatmap.css";

interface AlignmentPoint {
  timestamp: number;
  alignment: number;
}

interface AlignmentHeatmapProps {
  history: AlignmentPoint[];
  maxCells?: number;
}

function heatColor(alignment: number): string {
  if (alignment >= 85) return "rgba(63, 185, 80, 0.85)";
  if (alignment >= 70) return "rgba(88, 166, 255, 0.80)";
  if (alignment >= 55) return "rgba(210, 153, 34, 0.80)";
  if (alignment >= 40) return "rgba(240, 136, 62, 0.80)";
  return "rgba(248, 81, 73, 0.85)";
}

export function AlignmentHeatmap({ history, maxCells = 60 }: AlignmentHeatmapProps) {
  if (!history || history.length === 0) {
    return (
      <div className="alignment-heatmap alignment-heatmap--empty">
        <span className="alignment-heatmap__placeholder">No alignment history</span>
      </div>
    );
  }

  const visible = history.slice(-maxCells);

  return (
    <div className="alignment-heatmap">
      <div className="alignment-heatmap__label">Alignment History</div>
      <div className="alignment-heatmap__grid">
        {visible.map((point, idx) => (
          <div
            key={idx}
            className="alignment-heatmap__cell"
            style={{ backgroundColor: heatColor(point.alignment) }}
            title={`${new Date(point.timestamp).toLocaleTimeString()} — ${point.alignment}%`}
          />
        ))}
      </div>
    </div>
  );
}
