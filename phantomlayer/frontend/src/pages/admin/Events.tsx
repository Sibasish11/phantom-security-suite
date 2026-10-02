import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { DetailDrawer } from '../../components/DetailDrawer';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";

type Severity = "critical" | "high" | "medium" | "low" | string;
type SeverityFilter = "all" | "critical" | "high" | "medium" | "low";
type DestinationFilter = "all" | "real" | "honeypot" | "blocked";

interface SecurityEvent {
  event_id: string;
  session_id: string;
  timestamp: string;
  event_type: string;
  source: string;
  original_target: string;
  final_target: string;
  operation: string;
  risk_score: number | null;
  severity: Severity;
  confidence: number | null;
  confidence_level?: string;
  suspicious: boolean;
  triggered_rules: string[];
  reasons: string[];
  routing_decision?: string;
  routing_reason?: string;
  gateway_success?: boolean;
  metadata?: Record<string, unknown>;
}

function formatDate(value: string) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function severityVariant(severity: Severity) {
  switch (severity.toLowerCase()) {
    case "critical":
      return "danger" as const;
    case "high":
      return "warning" as const;
    case "medium":
      return "info" as const;

    case "low":
      return "info" as const;

    default:
      return "neutral" as const;
  }
}

function getDestination(event: SecurityEvent) {
  const target = (
    event.final_target ||
    event.routing_decision ||
    ""
  ).toLowerCase();

  if (target.includes("honeypot")) {
    return "honeypot";
  }

  if (
    target.includes("block") ||
    target.includes("reject") ||
    target.includes("deny")
  ) {
    return "blocked";
  }

  return target === 'real' ? 'real' : 'assessment';
}

function destinationLabel(destination: string) {
  switch (destination) {
    case "honeypot":
      return "Honeypot";

    case "blocked":
      return "Blocked";

    case "real":
      return "Real";

    default:
      return "Assessment";
  }
}

function shortId(value: string) {
  if (!value) return "—";

  if (value.length <= 18) {
    return value;
  }

  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

export function Events() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [destinationFilter, setDestinationFilter] =
    useState<DestinationFilter>("all");

  const [selectedEvent, setSelectedEvent] =
    useState<SecurityEvent | null>(null);

  const loadEvents = useCallback(async (silent = false) => {
    try {
      if (silent) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response = await apiGet<{events?: Record<string, unknown>[]} | Record<string, unknown>[]>(
        "/security/events?limit=200",
      );
      const rows = Array.isArray(response) ? response : response.events || [];
      setEvents(rows.map(row => ({
        ...row,
        event_id: String(row.event_id || ''), session_id: String(row.session_id || ''),
        timestamp: String(row.timestamp || ''), event_type: String(row.event_type || 'assessment'),
        source: String(row.source || ''), original_target: String(row.original_target || ''),
        final_target: String(row.final_target || ''), operation: String(row.operation || ''),
        risk_score: typeof row.risk_score === 'number' ? row.risk_score : null,
        severity: String(row.severity || 'unrated'), confidence: typeof row.confidence === 'number' ? row.confidence : null,
        suspicious: row.suspicious === true,
        triggered_rules: Array.isArray(row.triggered_rules) ? row.triggered_rules.map(rule => typeof rule === 'string' ? rule : String(rule?.rule || rule?.name || rule?.rule_id || 'Recorded rule')) : [],
        reasons: Array.isArray(row.reasons) ? row.reasons.map(String) : [],
      })));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load security events.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadEvents(true);
    }, 10000);

    return () => window.clearInterval(interval);
  }, [loadEvents]);

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLowerCase();

    return events.filter((event) => {
      const matchesSeverity =
        severity === "all" ||
        event.severity.toLowerCase() === severity;

      const matchesDestination =
        destinationFilter === "all" ||
        getDestination(event) === destinationFilter;

      if (!matchesSeverity || !matchesDestination) {
        return false;
      }

      if (!query) {
        return true;
      }

      const searchable = [
        event.event_id,
        event.session_id,
        event.event_type,
        event.source,
        event.operation,
        event.original_target,
        event.final_target,
        event.routing_decision,
        ...event.triggered_rules,
        ...event.reasons,
      ]
        .join(" ")
        .toLowerCase();

      return searchable.includes(query);
    });
  }, [events, search, severity, destinationFilter]);

  const stats = useMemo(() => {
    return {
      total: events.length,

      suspicious: events.filter(
        (event) => event.suspicious,
      ).length,

      honeypot: events.filter(
        (event) => getDestination(event) === "honeypot",
      ).length,

      blocked: events.filter(
        (event) => getDestination(event) === "blocked",
      ).length,

      critical: events.filter(
        (event) => event.severity.toLowerCase() === "critical",
      ).length,
    };
  }, [events]);

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="module-page">
      <section className="module-title">
        <div>
          <p className="eyebrow">SECURITY TELEMETRY</p>

          <h1>Security events</h1>

          <p className="module-description">
            Recorded security telemetry from your organization's agents and integrations.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() => void loadEvents(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="alert alert-danger">
          <strong>Unable to load events.</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="metrics-grid">
        <article className="metric-card cyan">
          <div className="metric-icon">Σ</div>

          <div className="metric-copy">
            <span>TOTAL EVENTS</span>
            <strong>{stats.total}</strong>
            <small>Recorded telemetry</small>
          </div>
        </article>

        <article className="metric-card amber">
          <div className="metric-icon">!</div>

          <div className="metric-copy">
            <span>SUSPICIOUS</span>
            <strong>{stats.suspicious}</strong>
            <small>Detection flagged</small>
          </div>
        </article>

        <article className="metric-card purple">
          <div className="metric-icon">H</div>

          <div className="metric-copy">
            <span>HONEYPOT</span>
            <strong>{stats.honeypot}</strong>
            <small>Routed to deception</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-icon">×</div>

          <div className="metric-copy">
            <span>BLOCKED</span>
            <strong>{stats.blocked}</strong>
            <small>Rejected requests</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-icon">C</div>

          <div className="metric-copy">
            <span>CRITICAL</span>
            <strong>{stats.critical}</strong>
            <small>Highest severity</small>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Event Stream</h2>
          </div>

          <div className="live-indicator">
            <span />
            LIVE TELEMETRY
          </div>
        </div>

        <div className="table-toolbar">
          <input
            className="input"
            placeholder="Search events, sessions, rules…"
            aria-label="Search event registry"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />

          <select
            className="input"
            value={severity}
            aria-label="Filter event severity"
            onChange={(event) =>
              setSeverity(
                event.target.value as SeverityFilter,
              )
            }
          >
            <option value="all">All severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            className="input"
            value={destinationFilter}
            aria-label="Filter event destination"
            onChange={(event) =>
              setDestinationFilter(
                event.target.value as DestinationFilter,
              )
            }
          >
            <option value="all">All destinations</option>
            <option value="honeypot">Honeypot</option>
            <option value="real">Real infrastructure</option>
            <option value="blocked">Blocked</option>
          </select>
        </div>

        <div className="table-scroll">
          {filteredEvents.length === 0 ? (
            <EmptyState
              title="No security events found"
              description={
                events.length === 0
                  ? "PhantomLayer has not recorded any security events yet."
                  : "Try changing the current filters."
              }
            />
          ) : (
            <ResponsiveTable>
              <thead>
                <tr>
                  <th>TIME</th>
                  <th>EVENT</th>
                  <th>OPERATION</th>
                  <th>SEVERITY</th>
                  <th>RISK</th>
                  <th>DESTINATION</th>
                  <th>SESSION</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {filteredEvents.map((event) => {
                  const target = getDestination(event);

                  return (
                    <tr
                      key={event.event_id}
                      onClick={() => setSelectedEvent(event)}
                    >
                      <td>{formatDate(event.timestamp)}</td>

                      <td>
                        <strong>
                          {event.event_type || "Security Event"}
                        </strong>

                        <br />

                        <small>{event.source || "—"}</small>
                      </td>

                      <td>
                        <code>{event.operation || "—"}</code>
                      </td>

                      <td>
                        <Badge
                          variant={severityVariant(
                            event.severity,
                          )}
                          size="small"
                        >
                          {event.severity || "unknown"}
                        </Badge>
                      </td>

                      <td>
                        <strong>{event.risk_score ?? '—'}</strong>
                      </td>

                      <td>
                        <Badge
                          variant={
                            target === "honeypot"
                              ? "purple"
                              : target === "blocked"
                                ? "danger"
                                : target === 'real' ? "success" : 'neutral'
                          }
                          size="small"
                        >
                          {destinationLabel(target)}
                        </Badge>
                      </td>

                      <td>
                        <code>
                          {shortId(event.session_id)}
                        </code>
                      </td>

                      <td>
                        <Button
                          variant="ghost"
                          onClick={(clickEvent) => {
                            clickEvent.stopPropagation();
                            setSelectedEvent(event);
                          }}
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </ResponsiveTable>
          )}
        </div>
      </section>

      {selectedEvent && (
        <DetailDrawer label="Event details" onClose={() => setSelectedEvent(null)}>
          <aside
            className="incident-drawer"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="drawer-close"
              onClick={() => setSelectedEvent(null)}
              aria-label="Close event details"
            >
              ×
            </button>

            <p className="eyebrow">EVENT DETAIL</p>

            <h2>
              {selectedEvent.event_type || "Security Event"}
            </h2>

            <div className="drawer-meta">
              <span>
                {formatDate(selectedEvent.timestamp)}
              </span>

              <Badge
                variant={severityVariant(
                  selectedEvent.severity,
                )}
                size="small"
              >
                {selectedEvent.severity}
              </Badge>
            </div>

            <div className="drawer-risk">
              <div className="risk-circle">
                <strong>{selectedEvent.risk_score ?? '—'}</strong>
                <span>RISK</span>
              </div>

              <div>
                <small>HEURISTIC CONFIDENCE</small>

                <strong>
                  {selectedEvent.confidence != null
                    ? `${Math.round(selectedEvent.confidence <= 1 ? selectedEvent.confidence * 100 : selectedEvent.confidence)}%`
                    : "—"}
                </strong>
              </div>
            </div>

            <section>
              <div className="drawer-label">
                SESSION
              </div>

              <code className="session-code">
                {selectedEvent.session_id}
              </code>
            </section>

            <section>
              <div className="drawer-label">
                REQUEST
              </div>

              <div className="drawer-copy">
                <strong>
                  Operation:
                </strong>{" "}
                {selectedEvent.operation || "—"}

                <br />

                <strong>
                  Source:
                </strong>{" "}
                {selectedEvent.source || "—"}

                <br />

                <strong>
                  Original target:
                </strong>{" "}
                {selectedEvent.original_target || "—"}

                <br />

                <strong>
                  Final target:
                </strong>{" "}
                {selectedEvent.final_target || "—"}
              </div>
            </section>

            <section>
              <div className="drawer-label">
                ROUTING
              </div>

              <div className="drawer-copy">
                <strong>
                  Decision:
                </strong>{" "}
                {selectedEvent.routing_decision || "—"}

                <br />

                <strong>
                  Reason:
                </strong>{" "}
                {selectedEvent.routing_reason || "—"}
              </div>
            </section>

            <section>
              <div className="drawer-label">
                TRIGGERED RULES
              </div>

              {selectedEvent.triggered_rules.length ? (
                <div className="operation-chips">
                  {selectedEvent.triggered_rules.map(
                    (rule) => (
                      <span key={rule}>
                        {rule}
                      </span>
                    ),
                  )}
                </div>
              ) : (
                <div className="drawer-copy">
                  No detection rules recorded.
                </div>
              )}
            </section>

            <section>
              <div className="drawer-label">
                DETECTION REASONS
              </div>

              {selectedEvent.reasons.length ? (
                <div className="recommendations">
                  {selectedEvent.reasons.map(
                    (reason, index) => (
                      <div
                        className="recommendation"
                        key={`${reason}-${index}`}
                      >
                        <span>›</span>
                        {reason}
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <div className="drawer-copy">
                  No detection reasons recorded.
                </div>
              )}
            </section>

            {selectedEvent.metadata &&
              Object.keys(selectedEvent.metadata).length >
                0 && (
                <section>
                  <div className="drawer-label">
                    METADATA
                  </div>

                  <pre className="session-code">
                    {JSON.stringify(
                      selectedEvent.metadata,
                      null,
                      2,
                    )}
                  </pre>
                </section>
              )}
          </aside>
        </DetailDrawer>
      )}
    </div>
  );
}