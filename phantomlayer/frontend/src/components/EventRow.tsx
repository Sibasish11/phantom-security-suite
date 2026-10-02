import type { SecurityEvent } from "../types/security";
import { StatusPill } from "./StatusPill";

interface EventRowProps {
  event: SecurityEvent;
  onClick?: () => void;
}

function formatOperation(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function getRiskClass(score: number): string {
  if (score >= 80) return "event-risk-critical";
  if (score >= 60) return "event-risk-high";
  if (score >= 40) return "event-risk-medium";
  return "event-risk-low";
}

export function EventRow({
  event,
  onClick,
}: EventRowProps) {
  /*
   * Keep the component compatible with the backend event
   * shape while allowing optional fields to be displayed
   * when they are available.
   */
  const rawEvent = event as unknown as Record<
    string,
    unknown
  >;

  const operation =
    typeof rawEvent.operation === "string"
      ? rawEvent.operation
      : "Unknown operation";

  const sourceIp =
    typeof rawEvent.source_ip === "string"
      ? rawEvent.source_ip
      : typeof rawEvent.ip_address === "string"
        ? rawEvent.ip_address
        : "Unknown source";

  const target =
    rawEvent.target === "honeypot"
      ? "honeypot"
      : "real";

  const attackStage =
    typeof rawEvent.attack_stage === "string"
      ? rawEvent.attack_stage
      : typeof rawEvent.stage === "string"
        ? rawEvent.stage
        : "unknown";

  const severity =
    typeof rawEvent.severity === "string"
      ? rawEvent.severity
      : "low";

  const timestamp =
    typeof rawEvent.timestamp === "string"
      ? rawEvent.timestamp
      : typeof rawEvent.created_at === "string"
        ? rawEvent.created_at
        : "";

  const riskScore =
    typeof rawEvent.risk_score === "number"
      ? rawEvent.risk_score
      : Number(rawEvent.risk_score ?? 0);

  return (
    <button
      type="button"
      className="event-row"
      onClick={onClick}
    >
      <div className="event-row-main">
        <div
          className={[
            "event-target-indicator",
            target === "honeypot"
              ? "event-target-honeypot"
              : "event-target-real",
          ].join(" ")}
        >
          {target === "honeypot" ? "◆" : "●"}
        </div>

        <div className="event-operation">
          <strong>
            {formatOperation(operation)}
          </strong>

          <span>{sourceIp}</span>
        </div>
      </div>

      <div className="event-stage">
        <span className="event-stage-label">
          {formatOperation(attackStage)}
        </span>
      </div>

      <div className="event-target">
        <span
          className={[
            "event-target-badge",
            target === "honeypot"
              ? "event-target-badge-honeypot"
              : "event-target-badge-real",
          ].join(" ")}
        >
          {target === "honeypot"
            ? "HONEYPOT"
            : "REAL"}
        </span>
      </div>

      <div className="event-risk">
        <span
          className={[
            "event-risk-value",
            getRiskClass(riskScore),
          ].join(" ")}
        >
          {riskScore}
        </span>

        <span className="event-risk-label">
          risk
        </span>
      </div>

      <div className="event-severity">
        <StatusPill
          status={severity}
          size="small"
        />
      </div>

      <div className="event-time">
        {timestamp
          ? formatTime(timestamp)
          : "—"}
      </div>

      <div className="event-arrow">
        →
      </div>
    </button>
  );
}