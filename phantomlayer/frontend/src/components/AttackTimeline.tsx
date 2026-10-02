import type {
  IncidentTimeline,
  IncidentTimelineEvent,
} from "../types/incident";
import { StatusPill } from "./StatusPill";

interface AttackTimelineProps {
  timeline: IncidentTimeline | null;
  loading?: boolean;
}

function formatLabel(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
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

function getSeverityClass(severity: string): string {
  if (severity === "critical") {
    return "attack-timeline-node-critical";
  }

  if (severity === "high") {
    return "attack-timeline-node-high";
  }

  if (severity === "medium") {
    return "attack-timeline-node-medium";
  }

  return "attack-timeline-node-low";
}

export function AttackTimeline({
  timeline,
  loading = false,
}: AttackTimelineProps) {
  if (loading) {
    return (
      <section className="attack-timeline">
        <div className="attack-timeline-header">
          <div>
            <span className="attack-timeline-kicker">
              INCIDENT TIMELINE
            </span>

            <h3>Attack activity</h3>
          </div>
        </div>

        <div className="attack-timeline-loading">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="attack-timeline-loading-row"
            >
              <div className="attack-timeline-loading-dot" />

              <div className="attack-timeline-loading-content">
                <div className="attack-timeline-loading-title" />

                <div className="attack-timeline-loading-line" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!timeline) {
    return (
      <section className="attack-timeline">
        <div className="attack-timeline-header">
          <div>
            <span className="attack-timeline-kicker">
              INCIDENT TIMELINE
            </span>

            <h3>Attack activity</h3>
          </div>
        </div>

        <div className="attack-timeline-empty">
          <div className="attack-timeline-empty-icon">
            ◌
          </div>

          <strong>No attack activity</strong>

          <span>
            Timeline events will appear here when
            PhantomLayer detects activity.
          </span>
        </div>
      </section>
    );
  }

  /*
   * Normalize the timeline here so this component stays
   * compatible with the backend response even if optional
   * fields differ from the frontend interface.
   */
  const rawTimeline =
    timeline as unknown as Record<string, unknown>;

  const rawEvents = Array.isArray(rawTimeline.events)
    ? rawTimeline.events
    : [];

  const events =
    rawEvents as unknown as IncidentTimelineEvent[];

  if (events.length === 0) {
    return (
      <section className="attack-timeline">
        <div className="attack-timeline-header">
          <div>
            <span className="attack-timeline-kicker">
              INCIDENT TIMELINE
            </span>

            <h3>Attack activity</h3>
          </div>
        </div>

        <div className="attack-timeline-empty">
          <div className="attack-timeline-empty-icon">
            ◌
          </div>

          <strong>No attack activity</strong>

          <span>
            Timeline events will appear here when
            PhantomLayer detects activity.
          </span>
        </div>
      </section>
    );
  }

  return (
    <section className="attack-timeline">
      <div className="attack-timeline-header">
        <div>
          <span className="attack-timeline-kicker">
            INCIDENT TIMELINE
          </span>

          <h3>Attack activity</h3>
        </div>

        <span className="attack-timeline-count">
          {events.length}{" "}
          {events.length === 1
            ? "event"
            : "events"}
        </span>
      </div>

      <div className="attack-timeline-list">
        {events.map((event, index) => {
          const rawEvent =
            event as unknown as Record<
              string,
              unknown
            >;

          const id =
            typeof rawEvent.id === "string"
              ? rawEvent.id
              : `${index}`;

          const attackStage =
            typeof rawEvent.attack_stage ===
            "string"
              ? rawEvent.attack_stage
              : typeof rawEvent.stage ===
                  "string"
                ? rawEvent.stage
                : "unknown";

          const title =
            typeof rawEvent.title === "string"
              ? rawEvent.title
              : formatLabel(attackStage);

          const description =
            typeof rawEvent.description ===
            "string"
              ? rawEvent.description
              : "Suspicious activity detected.";

          const severity =
            typeof rawEvent.severity ===
            "string"
              ? rawEvent.severity
              : "low";

          const operation =
            typeof rawEvent.operation ===
            "string"
              ? rawEvent.operation
              : "";

          const target =
            typeof rawEvent.target === "string"
              ? rawEvent.target
              : "";

          const timestamp =
            typeof rawEvent.created_at ===
            "string"
              ? rawEvent.created_at
              : typeof rawEvent.timestamp ===
                  "string"
                ? rawEvent.timestamp
                : "";

          return (
            <div
              key={id}
              className="attack-timeline-event"
            >
              <div className="attack-timeline-track">
                <div
                  className={[
                    "attack-timeline-node",
                    getSeverityClass(severity),
                  ].join(" ")}
                />

                {index < events.length - 1 && (
                  <div className="attack-timeline-line" />
                )}
              </div>

              <div className="attack-timeline-event-content">
                <div className="attack-timeline-event-top">
                  <div>
                    <span className="attack-timeline-stage">
                      {formatLabel(attackStage)}
                    </span>

                    <h4>{title}</h4>
                  </div>

                  <StatusPill
                    status={severity}
                    size="small"
                  />
                </div>

                <p>{description}</p>

                <div className="attack-timeline-meta">
                  {timestamp && (
                    <span>
                      {formatTime(timestamp)}
                    </span>
                  )}

                  {operation && (
                    <>
                      <span className="attack-timeline-meta-separator">
                        •
                      </span>

                      <span>
                        {formatLabel(operation)}
                      </span>
                    </>
                  )}

                  {target && (
                    <>
                      <span className="attack-timeline-meta-separator">
                        •
                      </span>

                      <span
                        className={
                          target === "honeypot"
                            ? "attack-timeline-honeypot"
                            : ""
                        }
                      >
                        {formatLabel(target)}
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}