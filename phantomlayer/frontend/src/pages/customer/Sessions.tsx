import { useEffect, useMemo, useState } from "react";

import { Badge } from "../../components/Badge";
import { EmptyState } from "../../components/EmptyState";

import { apiGet } from "../../lib/api";

interface SecurityEvent {
  event_id?: string;
  session_id?: string;
  timestamp?: string;
  event_type?: string;
  final_target?: string;
  operation?: string;
  risk_score?: number;
  severity?: string;
  suspicious?: boolean;
  triggered_rules?: unknown[];
}

interface EventsResponse {
  events?: SecurityEvent[];
  total?: number;
}

interface SessionSummary {
  sessionId: string;
  latestEvent: SecurityEvent;
  events: SecurityEvent[];
  risk: number;
  destination: string;
  operations: string[];
  rules: string[];
  lastSeen?: string;
}

function label(value?: string): string {
  if (!value) {
    return "Unknown";
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function formatTime(value?: string): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDate(value?: string): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleDateString([], {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function targetVariant(
  target?: string,
) {
  switch (target) {
    case "real":
      return "success" as const;

    case "honeypot":
      return "purple" as const;

    case "blocked":
      return "danger" as const;

    default:
      return "neutral" as const;
  }
}

function riskVariant(
  risk = 0,
) {
  if (risk >= 70) {
    return "danger" as const;
  }

  if (risk >= 40) {
    return "warning" as const;
  }

  return "info" as const;
}

function extractRules(
  event: SecurityEvent,
): string[] {
  if (!Array.isArray(event.triggered_rules)) {
    return [];
  }

  return event.triggered_rules
    .map((rule) => {
      if (
        typeof rule === "string"
      ) {
        return rule;
      }

      if (
        typeof rule === "object" &&
        rule !== null &&
        "rule" in rule
      ) {
        const value =
          (
            rule as {
              rule?: unknown;
            }
          ).rule;

        return typeof value ===
          "string"
          ? value
          : "";
      }

      return "";
    })
    .filter(Boolean);
}

export function Sessions() {
  const [events, setEvents] =
    useState<SecurityEvent[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [selectedSession, setSelectedSession] =
    useState<string | null>(null);

  const [targetFilter, setTargetFilter] =
    useState("all");

  async function loadEvents() {
    try {
      setError(null);

      const response =
        await apiGet<EventsResponse>(
          "/security/events?limit=1000",
        );

      setEvents(
        Array.isArray(response.events)
          ? response.events
          : [],
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load attack sessions.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadEvents();

    const interval =
      window.setInterval(() => {
        void loadEvents();
      }, 10000);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const sessions =
    useMemo<SessionSummary[]>(() => {
      const grouped =
        new Map<
          string,
          SecurityEvent[]
        >();

      for (const event of events) {
        if (!event.session_id) {
          continue;
        }

        const current =
          grouped.get(
            event.session_id,
          ) ?? [];

        current.push(event);

        grouped.set(
          event.session_id,
          current,
        );
      }

      return Array.from(
        grouped.entries(),
      )
        .map(
          ([sessionId, sessionEvents]) => {
            const sorted =
              [...sessionEvents].sort(
                (a, b) => {
                  const aTime =
                    a.timestamp
                      ? new Date(
                          a.timestamp,
                        ).getTime()
                      : 0;

                  const bTime =
                    b.timestamp
                      ? new Date(
                          b.timestamp,
                        ).getTime()
                      : 0;

                  return (
                    bTime - aTime
                  );
                },
              );

            const latest =
              sorted[0];

            const risk = Math.max(
              ...sessionEvents.map(
                (event) =>
                  event.risk_score ?? 0,
              ),
            );

            const operations =
              Array.from(
                new Set(
                  sessionEvents
                    .map(
                      (event) =>
                        event.operation,
                    )
                    .filter(
                      (
                        operation,
                      ): operation is string =>
                        Boolean(operation),
                    ),
                ),
              );

            const rules =
              Array.from(
                new Set(
                  sessionEvents.flatMap(
                    extractRules,
                  ),
                ),
              );

            return {
              sessionId,
              latestEvent: latest,
              events: sorted,
              risk,
              destination:
                latest.final_target ??
                "unknown",
              operations,
              rules,
              lastSeen:
                latest.timestamp,
            };
          },
        )
        .sort(
          (a, b) =>
            (b.lastSeen
              ? new Date(
                  b.lastSeen,
                ).getTime()
              : 0) -
            (a.lastSeen
              ? new Date(
                  a.lastSeen,
                ).getTime()
              : 0),
        );
    }, [events]);

  const filteredSessions =
    sessions.filter(
      (session) =>
        targetFilter === "all" ||
        session.destination ===
          targetFilter,
    );

  const selected =
    sessions.find(
      (session) =>
        session.sessionId ===
        selectedSession,
    );

  return (
    <div className="customer-sessions-page">
      {/* HEADER */}

      <section className="customer-page-header">
        <div>
          <span className="customer-eyebrow">
            ATTACK TRACKING
          </span>

          <h1>
            Attack sessions
          </h1>

          <p>
            Suspicious activity correlated into
            individual attacker sessions.
          </p>
        </div>

        <div className="sessions-total">
          <strong>
            {sessions.length}
          </strong>

          <span>
            SESSIONS OBSERVED
          </span>
        </div>
      </section>

      {/* ERROR */}

      {error && (
        <div className="customer-error-message">
          <span>!</span>
          <p>{error}</p>
        </div>
      )}

      {/* TOOLBAR */}

      <section className="sessions-toolbar">
        <div>
          <span>
            DESTINATION
          </span>

          <div className="sessions-filter-buttons">
            {[
              ["all", "ALL"],
              ["honeypot", "HONEYPOT"],
              ["real", "REAL"],
              ["blocked", "BLOCKED"],
            ].map(
              ([value, text]) => (
                <button
                  key={value}
                  type="button"
                  className={
                    targetFilter ===
                    value
                      ? "sessions-filter-active"
                      : ""
                  }
                  onClick={() =>
                    setTargetFilter(
                      value,
                    )
                  }
                >
                  {text}
                </button>
              ),
            )}
          </div>
        </div>

        <button
          type="button"
          className="sessions-refresh"
          onClick={() => {
            setLoading(true);
            void loadEvents();
          }}
        >
          ↻ Refresh
        </button>
      </section>

      {/* SESSION GRID */}

      {loading ? (
        <div className="sessions-loading">
          <div className="customer-loading-orb">
            ◎
          </div>

          <strong>
            Correlating attack sessions...
          </strong>

          <span>
            Processing security telemetry.
          </span>
        </div>
      ) : filteredSessions.length ===
        0 ? (
        <EmptyState
          icon="◎"
          title="No attack sessions"
          description="Correlated attacker sessions will appear here when PhantomLayer observes session activity."
        />
      ) : (
        <div className="sessions-grid">
          {filteredSessions.map(
            (session) => {
              const isSelected =
                selectedSession ===
                session.sessionId;

              return (
                <button
                  type="button"
                  key={session.sessionId}
                  className={`attack-session-card ${
                    isSelected
                      ? "attack-session-selected"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedSession(
                      isSelected
                        ? null
                        : session.sessionId,
                    )
                  }
                >
                  <div className="attack-session-top">
                    <div className="attack-session-status">
                      <span />
                      OBSERVED
                    </div>

                    <Badge
                      variant={targetVariant(
                        session.destination,
                      )}
                      size="small"
                    >
                      {session.destination.toUpperCase()}
                    </Badge>
                  </div>

                  <code>
                    {session.sessionId}
                  </code>

                  <div className="attack-session-operation">
                    <span>
                      LAST OPERATION
                    </span>

                    <strong>
                      {label(
                        session
                          .latestEvent
                          .operation,
                      )}
                    </strong>
                  </div>

                  <div className="attack-session-stats">
                    <div>
                      <span>RISK</span>
                      <strong>
                        {session.risk}
                      </strong>
                    </div>

                    <div>
                      <span>EVENTS</span>
                      <strong>
                        {
                          session
                            .events
                            .length
                        }
                      </strong>
                    </div>

                    <div>
                      <span>OPS</span>
                      <strong>
                        {
                          session
                            .operations
                            .length
                        }
                      </strong>
                    </div>
                  </div>

                  <div className="attack-session-footer">
                    <span>
                      Last seen{" "}
                      {formatTime(
                        session.lastSeen,
                      )}
                    </span>

                    <span>
                      {isSelected
                        ? "−"
                        : "+"}
                    </span>
                  </div>
                </button>
              );
            },
          )}
        </div>
      )}

      {/* SELECTED SESSION */}

      {selected && (
        <section className="session-detail-panel">
          <div className="session-detail-header">
            <div>
              <span className="customer-eyebrow">
                SESSION DETAIL
              </span>

              <h2>
                {selected.sessionId}
              </h2>

              <p>
                Observed{" "}
                {formatDate(
                  selected.lastSeen,
                )}{" "}
                ·{" "}
                {selected.events.length}{" "}
                events
              </p>
            </div>

            <Badge
              variant={riskVariant(
                selected.risk,
              )}
            >
              RISK {selected.risk}
            </Badge>
          </div>

          <div className="session-detail-grid">
            <div>
              <span>
                DESTINATION
              </span>

              <Badge
                variant={targetVariant(
                  selected.destination,
                )}
              >
                {selected.destination.toUpperCase()}
              </Badge>
            </div>

            <div>
              <span>
                OPERATIONS
              </span>

              <strong>
                {selected.operations.length}
              </strong>
            </div>

            <div>
              <span>
                TRIGGERED RULES
              </span>

              <strong>
                {selected.rules.length}
              </strong>
            </div>
          </div>

          <div className="session-activity">
            <div className="session-activity-heading">
              <span>
                ACTIVITY TIMELINE
              </span>
            </div>

            {selected.events.map(
              (event, index) => (
                <div
                  className="session-activity-row"
                  key={
                    event.event_id ??
                    `${event.timestamp}-${index}`
                  }
                >
                  <span className="session-activity-line" />

                  <div className="session-activity-time">
                    {formatTime(
                      event.timestamp,
                    )}
                  </div>

                  <div className="session-activity-main">
                    <strong>
                      {label(
                        event.operation,
                      )}
                    </strong>

                    <span>
                      {label(
                        event.event_type,
                      )}
                    </span>
                  </div>

                  <span className="session-activity-risk">
                    {event.risk_score ??
                      0}
                  </span>

                  <Badge
                    variant={targetVariant(
                      event.final_target,
                    )}
                    size="small"
                  >
                    {(
                      event.final_target ??
                      "unknown"
                    ).toUpperCase()}
                  </Badge>
                </div>
              ),
            )}
          </div>

          {selected.operations.length >
            0 && (
            <div className="session-tags">
              <span>
                OPERATIONS OBSERVED
              </span>

              <div>
                {selected.operations.map(
                  (operation) => (
                    <code
                      key={operation}
                    >
                      {operation}
                    </code>
                  ),
                )}
              </div>
            </div>
          )}

          {selected.rules.length >
            0 && (
            <div className="session-tags">
              <span>
                SECURITY RULES
              </span>

              <div>
                {selected.rules.map(
                  (rule) => (
                    <code key={rule}>
                      {rule}
                    </code>
                  ),
                )}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}