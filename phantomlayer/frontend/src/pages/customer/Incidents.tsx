import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";
import { StatusPill } from "../../components/StatusPill";
import { useOrganization } from '../../hooks/useOrganization';
import { bankSessionDomain } from '../../lib/sessionContext';
import {
  analyzeIncident,
  getIncident,
  getIncidents,
  getIncidentTimeline,
} from "../../lib/api";

type Severity = "low" | "medium" | "high" | "critical";

type IncidentRecord = {
  incident_id: string;
  session_id: string;
  severity: string;
  risk_score: number;
  attack_stage?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  source?: string;
  operations_observed?: string[];
  triggered_rules?: string[];
  routing_decisions?: string[];
  interaction_count?: number;
};

type TimelineItem = {
  timestamp?: string;
  operation?: string;
  event_type?: string;
  attack_stage?: string;
  risk_score?: number;
  severity?: string;
  target?: string;
  final_target?: string;
  triggered_rules?: string[];
  routing_decision?: string;
  description?: string;
};

type IncidentAnalysis = {
  incident_summary?: string;
  observed_behavior?: string;
  risk_assessment?: string;
  likely_objective?: string;
  operations_performed?: string[];
  sensitive_resources_targeted?: string[];
  exposed_synthetic_entities?: Record<string, number>;
  attack_stage_progression?: string[];
  defensive_recommendations?: {
    action_type?: string;
    description?: string;
    priority?: string;
  }[];
  suspicious_patterns?: {
    pattern_name?: string;
    description?: string;
    confidence?: string;
  }[];
  limitations?: string;
  analysis_provider?: string;
};

type IncidentDetail = IncidentRecord & {
  analysis?: IncidentAnalysis;
};

function label(value?: string) {
  return (value || "unknown").replaceAll("_", " ");
}

function formatDate(value?: string) {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function severityVariant(severity?: string) {
  switch ((severity || "").toLowerCase()) {
    case "critical":
      return "danger" as const;
    case "high":
      return "warning" as const;
    case "medium":
      return "info" as const;
    default:
      return "neutral" as const;
  }
}

function riskClass(score: number) {
  if (score >= 76) return "critical";
  if (score >= 51) return "high";
  if (score >= 31) return "medium";
  return "low";
}

function normalizeIncidents(payload: unknown): IncidentRecord[] {
  if (Array.isArray(payload)) {
    return payload as IncidentRecord[];
  }

  if (
    payload &&
    typeof payload === "object" &&
    "incidents" in payload &&
    Array.isArray((payload as { incidents?: unknown }).incidents)
  ) {
    return (payload as { incidents: IncidentRecord[] }).incidents;
  }

  return [];
}

function normalizeTimeline(payload: unknown): TimelineItem[] {
  if (Array.isArray(payload)) {
    return payload as TimelineItem[];
  }

  if (
    payload &&
    typeof payload === "object" &&
    "timeline" in payload &&
    Array.isArray((payload as { timeline?: unknown }).timeline)
  ) {
    return (payload as { timeline: TimelineItem[] }).timeline;
  }

  return [];
}

export function Incidents() {
  const {agents, domains} = useOrganization();
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [selected, setSelected] = useState<IncidentDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);

  const [filter, setFilter] = useState<"all" | Severity>("all");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  async function loadIncidents() {
    try {
      setError("");

      const response = await getIncidents();
      setIncidents(normalizeIncidents(response));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load security incidents.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function openIncident(incident: IncidentRecord) {
    setSelected(incident);
    setTimeline([]);
    setDetailError("");
    setDetailLoading(true);

    try {
      const [detailResponse, timelineResponse] = await Promise.all([
        getIncident(incident.incident_id),
        getIncidentTimeline(incident.incident_id),
      ]);

      const detail =
        detailResponse && typeof detailResponse === "object"
          ? (detailResponse as unknown as IncidentDetail)
          : incident;

      setSelected({
        ...incident,
        ...detail,
      });

      setTimeline(normalizeTimeline(timelineResponse));
    } catch (err) {
      setDetailError(
        err instanceof Error
          ? err.message
          : "Unable to load incident details.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function runAnalysis() {
    if (!selected?.session_id) return;

    setAnalysisLoading(true);
    setDetailError("");

    try {
      const response = await analyzeIncident(selected.session_id, Boolean(selected.analysis));

      const analysis =
        response && typeof response === "object"
          ? response
          : undefined;

      setSelected((current) =>
        current
          ? {
              ...current,
              status: 'completed',
              analysis:
                analysis && "analysis" in analysis
                  ? (analysis as { analysis?: IncidentAnalysis }).analysis
                  : (analysis as IncidentAnalysis | undefined),
            }
          : current,
      );
    } catch (err) {
      setDetailError(
        err instanceof Error
          ? err.message
          : "Unable to analyze this incident.",
      );
    } finally {
      setAnalysisLoading(false);
    }
  }

  useEffect(() => {
    void loadIncidents();

    const interval = window.setInterval(() => {
      void loadIncidents();
    }, 10000);

    return () => window.clearInterval(interval);
  }, []);

  const filteredIncidents = useMemo(() => {
    if (filter === "all") {
      return incidents;
    }

    return incidents.filter(
      (incident) => incident.severity.toLowerCase() === filter,
    );
  }, [incidents, filter]);

  const counts = useMemo(
    () => ({
      total: incidents.length,
      critical: incidents.filter(
        (incident) => incident.severity.toLowerCase() === "critical",
      ).length,
      high: incidents.filter(
        (incident) => incident.severity.toLowerCase() === "high",
      ).length,
      open: incidents.filter((incident) =>
        ["pending", "failed"].includes(incident.status.toLowerCase()),
      ).length,
    }),
    [incidents],
  );

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="customer-incidents-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">SECURITY OPERATIONS</p>
          <h1>Incidents</h1>
          <p>
            Investigate suspicious activity detected by PhantomLayer across
            your protected infrastructure.
          </p>
        </div>

        <Button variant="secondary" onClick={() => void loadIncidents()}>
          Refresh
        </Button>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>Incident feed unavailable</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="incident-summary-grid">
        <article className="incident-summary-card">
          <span>Total incidents</span>
          <strong>{counts.total}</strong>
        </article>

        <article className="incident-summary-card">
          <span>Critical</span>
          <strong className="danger-number">{counts.critical}</strong>
        </article>

        <article className="incident-summary-card">
          <span>High severity</span>
          <strong>{counts.high}</strong>
        </article>

        <article className="incident-summary-card">
          <span>Awaiting analysis</span>
          <strong>{counts.open}</strong>
        </article>
      </section>

      <section className="incident-workspace">
        <div className="incident-list-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">DETECTED ACTIVITY</p>
              <h2>Incident queue</h2>
            </div>

            <div className="incident-filters">
              {(["all", "critical", "high", "medium", "low"] as const).map(
                (value) => (
                  <button
                    key={value}
                    className={
                      filter === value
                        ? "incident-filter active"
                        : "incident-filter"
                    }
                    aria-pressed={filter === value}
                    onClick={() => setFilter(value)}
                  >
                    {label(value)}
                  </button>
                ),
              )}
            </div>
          </div>

          {filteredIncidents.length === 0 ? (
            <EmptyState
              title="No incidents found"
              description={
                filter === "all"
                  ? "PhantomLayer has not recorded any incidents for this organization yet."
                  : `No ${filter} severity incidents are currently recorded.`
              }
            />
          ) : (
            <div className="incident-list">
              {filteredIncidents.map((incident) => {
                const isSelected =
                  selected?.incident_id === incident.incident_id;

                return (
                  <button
                    key={incident.incident_id}
                    className={
                      isSelected
                        ? "incident-row selected"
                        : "incident-row"
                    }
                    onClick={() => void openIncident(incident)}
                  >
                    <div className="incident-row-main">
                      <div className="incident-row-title">
                        <span className="incident-id">
                          {incident.incident_id.slice(0, 8)}
                        </span>

                        <Badge
                          variant={severityVariant(incident.severity)}
                          size="small"
                        >
                          {label(incident.severity)}
                        </Badge>
                      </div>

                      <strong>
                        {label(incident.attack_stage || "suspicious activity")}
                      </strong>

                      {bankSessionDomain(incident.session_id, agents, domains) && <span className="incident-domain">{bankSessionDomain(incident.session_id, agents, domains)?.domain}</span>}
                      <span className="incident-session">
                        {incident.session_id?.startsWith('bank:') ? 'PhantomBank' : 'Session'} · {incident.session_id?.slice(-12) || "—"}
                      </span>
                    </div>

                    <div className="incident-row-risk">
                      <span
                        className={`risk-score ${riskClass(
                          incident.risk_score,
                        )}`}
                      >
                        {incident.risk_score}
                      </span>

                      <span className="incident-row-status">
                        {label(incident.status)}
                      </span>

                      <time>{formatDate(incident.created_at)}</time>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <aside className="incident-detail-panel">
          {!selected ? (
            <div className="incident-detail-empty">
              <div className="incident-detail-icon">◈</div>
              <h3>Select an incident</h3>
              <p>
                Choose an incident from the queue to inspect its timeline,
                routing decisions, rules, and advisory analysis.
              </p>
            </div>
          ) : detailLoading ? (
            <div className="incident-detail-loading">
              <div className="loading-orbit" />
              <p>Loading incident telemetry…</p>
            </div>
          ) : (
            <>
              <div className="incident-detail-header">
                <div>
                  <p className="eyebrow">INCIDENT DETAIL</p>
                  <h2>{selected.incident_id.slice(0, 12)}</h2>
                  <span>
                    Created {formatDate(selected.created_at)}
                  </span>
                </div>

                <Badge
                  variant={severityVariant(selected.severity)}
                  size="small"
                >
                  {label(selected.severity)}
                </Badge>
              </div>

              <Link className="ui-primary incident-detail-open" to={`/dashboard/incidents/${selected.incident_id}`}>Open full investigation ↗</Link>

              {detailError && (
                <div className="customer-alert customer-alert-danger" role="alert">
                  {detailError}
                </div>
              )}

              <div className="incident-detail-metrics">
                <div>
                  <span>Risk score</span>
                  <strong
                    className={`detail-risk ${riskClass(
                      selected.risk_score,
                    )}`}
                  >
                    {selected.risk_score}/100
                  </strong>
                </div>

                <div>
                  <span>Status</span>
                  <StatusPill status={selected.status} />
                </div>

                <div>
                  <span>Attack stage</span>
                  <strong>
                    {label(selected.attack_stage || "unknown")}
                  </strong>
                </div>

                <div>
                  <span>Interactions</span>
                  <strong>{selected.interaction_count ?? "—"}</strong>
                </div>
              </div>

              <div className="incident-detail-section">
                <div className="section-title-row">
                  <div>
                    <p className="eyebrow">SESSION</p>
                    <h3>Attack context</h3>
                  </div>
                </div>

                <div className="incident-context-grid">
                  <div>
                    <span>Session ID</span>
                    <code>{selected.session_id || "Unavailable"}</code>
                  </div>

                  <div>
                    <span>Source</span>
                    <strong>{selected.source || "Security gateway"}</strong>
                  </div>
                </div>
              </div>

              <div className="incident-detail-section">
                <div className="section-title-row">
                  <div>
                    <p className="eyebrow">TELEMETRY</p>
                    <h3>Attack timeline</h3>
                  </div>
                </div>

                {timeline.length === 0 ? (
                  <p className="muted-copy">
                    No timeline events are available for this incident.
                  </p>
                ) : (
                  <div className="incident-timeline">
                    {timeline.map((item, index) => (
                      <div
                        className="incident-timeline-item"
                        key={`${item.timestamp || "event"}-${index}`}
                      >
                        <div className="timeline-marker" />

                        <div className="timeline-content">
                          <div className="timeline-top">
                            <strong>
                              {item.operation ||
                                item.event_type ||
                                "Security event"}
                            </strong>

                            {typeof item.risk_score === "number" && (
                              <span>
                                Risk {item.risk_score}
                              </span>
                            )}
                          </div>

                          <p>
                            {item.description ||
                              `${label(
                                item.attack_stage || selected.attack_stage,
                              )} activity detected.`}
                          </p>

                          <small>
                            {formatDate(item.timestamp)}
                            {item.final_target
                              ? ` · ${item.final_target}`
                              : item.target
                                ? ` · ${item.target}`
                                : ""}
                          </small>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="incident-detail-section">
                <div className="section-title-row">
                  <div>
                    <p className="eyebrow">SECURITY SIGNALS</p>
                    <h3>Triggered rules</h3>
                  </div>
                </div>

                {selected.triggered_rules &&
                selected.triggered_rules.length > 0 ? (
                  <div className="rule-list">
                    {selected.triggered_rules.map((rule) => (
                      <Badge key={rule} variant="warning" size="small">
                        {label(rule)}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="muted-copy">
                    No rule names were attached to this incident record.
                  </p>
                )}
              </div>

              <div className="incident-detail-section">
                <div className="section-title-row">
                  <div>
                    <p className="eyebrow">AI INCIDENT ANALYSIS</p>
                    <h3>Analyst intelligence</h3>
                  </div>

                  {!selected.analysis && selected.session_id && (
                    <Button
                      variant="secondary"
                      onClick={() => void runAnalysis()}
                      disabled={analysisLoading}
                    >
                      {analysisLoading
                        ? "Analyzing…"
                        : "Analyze incident"}
                    </Button>
                  )}
                </div>

                {!selected.analysis ? (
                  <div className="analysis-empty">
                    <p>
                      Run the incident analysis pipeline to generate an
                      advisory investigation summary from the sanitized
                      session telemetry.
                    </p>

                    <small>
                      AI analysis does not control PhantomLayer routing
                      decisions.
                    </small>
                  </div>
                ) : (
                  <div className="analysis-content">
                    {selected.analysis.incident_summary && (
                      <div className="analysis-block">
                        <span>Summary</span>
                        <p>{selected.analysis.incident_summary}</p>
                      </div>
                    )}

                    {selected.analysis.observed_behavior && (
                      <div className="analysis-block">
                        <span>Observed behavior</span>
                        <p>{selected.analysis.observed_behavior}</p>
                      </div>
                    )}

                    {selected.analysis.likely_objective && (
                      <div className="analysis-block">
                        <span>Likely objective</span>
                        <p>{selected.analysis.likely_objective}</p>
                      </div>
                    )}

                    {selected.analysis.risk_assessment && (
                      <div className="analysis-block">
                        <span>Risk assessment</span>
                        <p>{selected.analysis.risk_assessment}</p>
                      </div>
                    )}

                    {selected.analysis.defensive_recommendations &&
                      selected.analysis.defensive_recommendations.length >
                        0 && (
                        <div className="analysis-block">
                          <span>Recommendations</span>

                          <div className="recommendation-list">
                            {selected.analysis.defensive_recommendations.map(
                              (recommendation, index) => (
                                <div
                                  className="recommendation-item"
                                  key={`${recommendation.action_type || "action"}-${index}`}
                                >
                                  <strong>
                                    {label(
                                      recommendation.action_type ||
                                        "defensive action",
                                    )}
                                  </strong>

                                  <p>
                                    {recommendation.description ||
                                      "No description provided."}
                                  </p>

                                  {recommendation.priority && (
                                    <Badge
                                      variant="info"
                                      size="small"
                                    >
                                      {label(
                                        recommendation.priority,
                                      )}
                                    </Badge>
                                  )}
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    {selected.analysis.limitations && (
                      <div className="analysis-limitations">
                        <strong>Analysis limitations</strong>
                        <p>{selected.analysis.limitations}</p>
                      </div>
                    )}

                    <div className="analysis-provider">
                      Provider:{" "}
                      {selected.analysis.analysis_provider || "unknown"}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </aside>
      </section>

      <div className="incident-footer-link">
        <Link to="/dashboard/sessions">
          ← View correlated attack sessions
        </Link>
      </div>
    </div>
  );
}