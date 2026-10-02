import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  accent?: "purple" | "cyan" | "green" | "yellow" | "red";
  loading?: boolean;
  onClick?: () => void;
}

export function MetricCard({
  label,
  value,
  description,
  icon,
  trend,
  trendDirection = "neutral",
  accent = "purple",
  loading = false,
  onClick,
}: MetricCardProps) {
  const className = [
    "metric-card",
    `metric-card-${accent}`,
    onClick ? "metric-card-clickable" : "",
  ]
    .filter(Boolean)
    .join(" ");

  if (loading) {
    return (
      <div className={`${className} metric-card-loading`}>
        <div className="metric-skeleton metric-skeleton-label" />
        <div className="metric-skeleton metric-skeleton-value" />
        <div className="metric-skeleton metric-skeleton-description" />
      </div>
    );
  }

  return (
    <div
      className={className}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(event) => {
        if (
          onClick &&
          (event.key === "Enter" ||
            event.key === " ")
        ) {
          event.preventDefault();
          onClick();
        }
      }}
    >
      <div className="metric-card-top">
        <span className="metric-card-label">
          {label}
        </span>

        {icon && (
          <span className="metric-card-icon">
            {icon}
          </span>
        )}
      </div>

      <div className="metric-card-value">
        {value}
      </div>

      <div className="metric-card-bottom">
        {description && (
          <span className="metric-card-description">
            {description}
          </span>
        )}

        {trend && (
          <span
            className={[
              "metric-card-trend",
              `metric-trend-${trendDirection}`,
            ].join(" ")}
          >
            {trendDirection === "up" && "↑"}
            {trendDirection === "down" && "↓"}
            {trendDirection === "neutral" && "•"}
            {" "}
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}