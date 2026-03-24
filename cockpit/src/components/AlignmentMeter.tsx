import "./AlignmentMeter.css";

interface AlignmentMeterProps {
  value: number;
  label?: string;
  showValue?: boolean;
}

function meterColor(value: number): string {
  if (value >= 85) return "var(--meter-excellent, #3fb950)";
  if (value >= 70) return "var(--meter-strong, #58a6ff)";
  if (value >= 55) return "var(--meter-moderate, #d29922)";
  if (value >= 40) return "var(--meter-low, #f0883e)";
  return "var(--meter-critical, #f85149)";
}

function meterTier(value: number): string {
  if (value >= 85) return "excellent";
  if (value >= 70) return "strong";
  if (value >= 55) return "moderate";
  if (value >= 40) return "low";
  return "critical";
}

export function AlignmentMeter({ value, label, showValue = true }: AlignmentMeterProps) {
  const color = meterColor(value);
  const tier = meterTier(value);

  return (
    <div className={`alignment-meter alignment-meter--${tier}`}>
      {label && <span className="alignment-meter__label">{label}</span>}
      <div className="alignment-meter__track">
        <div
          className="alignment-meter__bar"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }}
        />
      </div>
      {showValue && <span className="alignment-meter__value">{value}%</span>}
    </div>
  );
}
