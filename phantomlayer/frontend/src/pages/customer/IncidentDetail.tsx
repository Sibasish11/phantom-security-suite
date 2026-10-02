import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { LoadingScreen } from "../../components/LoadingScreen";
import { StatusPill } from "../../components/StatusPill";
import { useOrganization } from '../../hooks/useOrganization';
import { bankSessionDomain } from '../../lib/sessionContext';
import {
  analyzeIncident,
  getIncident,
  getIncidentTimeline,
} from "../../lib/api";

type Incident = {
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

type TimelineEvent = {
  event_id?: string;
  timestamp?: string;
  operation?: string;
  event_type?: string;
  attack_stage?: string;
  risk_score?: number;
  severity?: string;
  original_target?: string;
  final_target?: string;
  routing_decision?: string;
  routing_reason?: string;
  triggered_rules?: string[];
  reasons?: string[];
  description?: string;
  success?: boolean;
  synthetic_exposure_counts?: Record<string, number>;
};

type Analysis = {
  session_id?: string;
  incident_summary?: string;
  attack_stage_progression?: string[];
  observed_behavior?: string;
  operations_performed?: string[];
  sensitive_resources_targeted?: string[];
  exposed_synthetic_entities?: Record<string, number>;
  risk_assessment?: string;
  likely_objective?: string;
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

type IncidentDetailResponse = Incident & {
  analysis?: Analysis;
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

function riskLevel(score: number) {
  if (score >= 76) return "critical";
  if (score >= 51) return "high";
  if (score >= 31) return "medium";
  return "low";
}

function normalizeTimeline(payload: unknown): TimelineEvent[] {
  if (Array.isArray(payload)) {
    return payload as TimelineEvent[];
  }

  if (
    payload &&
    typeof payload === "object" &&
    "timeline" in payload &&
    Array.isArray((payload as { timeline?: unknown }).timeline)
  ) {
    return (payload as { timeline: TimelineEvent[] }).timeline;
  }

  return [];
}

function getTarget(event: TimelineEvent) {
  return event.final_target || event.original_target || "unknown";
}

export function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const {agents, domains} = useOrganization();

  const [incident, setIncident] = useState<IncidentDetailResponse | null>(
    null,
  );
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadIncident() {
    if (!id) {
      setError("No incident ID was provided.");
      setLoading(false);
      return;
    }

    setRefreshing(true);
    try {
      setError("");

      const [incidentResponse, timelineResponse] = await Promise.all([
        getIncident(id),
        getIncidentTimeline(id),
      ]);

      setIncident(
        incidentResponse as unknown as IncidentDetailResponse,
      );

      setTimeline(normalizeTimeline(timelineResponse));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load this incident.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function runAnalysis() {
    if (!incident?.session_id) return;

    setAnalysisLoading(true);
    setError("");

    try {
      const response = await analyzeIncident(incident.session_id, Boolean(incident.analysis));

      if (
        response &&
        typeof response === "object" &&
        "analysis" in response
      ) {
        const analysis = (
          response as { analysis?: Analysis }
        ).analysis;

        setIncident((current) =>
          current
            ? {
                ...current,
                status: 'completed',
                analysis,
              }
            : current,
        );
      } else {
        setIncident((current) =>
          current
            ? {
                ...current,
                analysis: response as Analysis,
              }
            : current,
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate incident analysis.",
      );
    } finally {
      setAnalysisLoading(false);
    }
  }

  useEffect(() => {
    void loadIncident();
  }, [id]);

  if (loading) {
    return <LoadingScreen />;
  }

  if (!incident) {
    return (
      <div className="incident-detail-error-page">
        <p className="eyebrow">INCIDENT INVESTIGATION</p>
        <h1>Incident unavailable</h1>
        <p>{error || "The requested incident could not be found."}</p>
        <Link to="/dashboard/incidents">← Back to incidents</Link>
      </div>
    );
  }

  const risk = riskLevel(incident.risk_score);
  const domain = bankSessionDomain(incident.session_id, agents, domains);

  return (
    <div className="customer-incident-detail-page">
      <div className="incident-detail-breadcrumb">
        <Link to="/dashboard/incidents">← Incident queue</Link>
      </div>

      {error && (
        <div className="customer-alert customer-alert-danger" role="alert">
          <strong>Investigation warning</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="incident-hero">
        <div>
          <p className="eyebrow">INCIDENT INVESTIGATION</p>

          <div className="incident-hero-title">
            <h1>{label(incident.attack_stage)} investigation</h1>

            <Badge
              variant={severityVariant(incident.severity)}
              size="small"
            >
              {label(incident.severity)}
            </Badge>
          </div>

          <p className="incident-hero-meta">
            {domain ? `${domain.domain} · ` : incident.session_id.startsWith('bank:') ? 'PhantomBank integration · ' : 'Tenant-owned session · '}
            Detected {formatDate(incident.created_at)}
            {incident.updated_at
              ? ` · Updated ${formatDate(incident.updated_at)}`
              : ""}
          </p>
        </div>

        <div className="incident-hero-actions">
          <Button variant="secondary" disabled={refreshing || analysisLoading} onClick={() => void loadIncident()}>
            {refreshing ? 'Refreshing…' : 'Refresh evidence'}
          </Button>
          {incident.session_id && (
            <Button
              variant="secondary"
              onClick={() => void runAnalysis()}
              loading={analysisLoading}
              disabled={refreshing}
            >
              {analysisLoading
                ? "Analyzing…"
                : incident.analysis
                  ? "Re-analyze"
                  : "Analyze incident"}
            </Button>
          )}
        </div>
      </section>

      <ol className="incident-pipeline" aria-label="Incident evidence pipeline">
        {[
          ['Detection', `${incident.triggered_rules?.length ?? 0} recorded rules`],
          ['Risk', `${incident.risk_score}/100 · deterministic`],
          ['Routing', incident.routing_decisions?.length ? incident.routing_decisions.map(value => value === 'honeypot' ? 'Isolated deception' : label(value)).join(', ') : 'See event evidence'],
          ['Deception', `${incident.interaction_count ?? timeline.length} interactions`],
          ['Telemetry', `${timeline.length} timeline entries`],
          ['Analysis', incident.analysis ? `${incident.analysis.analysis_provider || 'Advisory'} · advisory` : 'Awaiting analysis'],
        ].map(([title, detail], index) => <li key={title}><span>0{index + 1}</span><strong>{title}</strong><small>{detail}</small></li>)}
      </ol>

      <section className="incident-stat-grid">
        <article>
          <span>Risk score</span>
          <strong className={`incident-big-risk ${risk}`}>
            {incident.risk_score}
          </strong>
          <small>out of 100</small>
        </article>

        <article>
          <span>Severity</span>
          <strong className="capitalize-text">
            {label(incident.severity)}
          </strong>
          <small>detected severity</small>
        </article>

        <article>
          <span>Attack stage</span>
          <strong className="capitalize-text">
            {label(incident.attack_stage)}
          </strong>
          <small>current classification</small>
        </article>

        <article>
          <span>Interactions</span>
          <strong>{incident.interaction_count ?? "—"}</strong>
          <small>observed interactions</small>
        </article>
      </section>

      <section className="incident-main-grid">
        <div className="incident-main-column">
          <section className="incident-card incident-context-card">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">SESSION CONTEXT</p>
                <h2>Attack session</h2>
              </div>

              <StatusPill status={incident.status} />
            </div>

            <div className="incident-session-grid">
              <div>
                <span>Incident ID</span>
                <code>{incident.incident_id}</code>
              </div>

              <div>
                <span>Session ID</span>
                <code>{incident.session_id || "Unavailable"}</code>
              </div>

              <div>
                <span>Source</span>
                <strong>
                  {incident.source || "Security gateway"}
                </strong>
              </div>

              <div>
                <span>Status</span>
                <strong className="capitalize-text">
                  {label(incident.status)}
                </strong>
              </div>
            </div>
          </section>

          <section className="incident-card incident-timeline-card" aria-labelledby="attack-timeline-title">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">ATTACK ACTIVITY</p>
                <h2 id="attack-timeline-title">Attack timeline</h2>
              </div>

              <span className="incident-card-count">
                {timeline.length} events
              </span>
            </div>

            {timeline.some(event => typeof event.risk_score === 'number') && <div className="timeline-risk-history" aria-label="Observed session risk progression">
              <div><span className="eyebrow">RISK PROGRESSION</span><small>Observed scores · chronological</small></div>
              <ol>{timeline.map((event, index) => typeof event.risk_score === 'number' && <li key={event.event_id || index} title={`${event.operation || 'Interaction'} · ${formatDate(event.timestamp)}`}><span>{String(index + 1).padStart(2, '0')}</span><strong className={riskLevel(event.risk_score)}>{event.risk_score}</strong><i aria-hidden="true" style={{height: `${Math.max(3, event.risk_score / 2)}px`}} /></li>)}</ol>
            </div>}
            <Link className="text-link timeline-events-link" to={`/dashboard/events?session=${encodeURIComponent(incident.session_id)}`}>Inspect this session's detection and routing events ↗</Link>
            {timeline.length === 0 ? (
              <div className="incident-empty-inline">
                No timeline events are available for this incident.
              </div>
            ) : (
              <div className="full-incident-timeline">
                {timeline.map((event, index) => (
                  <article
                    className="full-timeline-event"
                    key={
                      event.event_id ||
                      `${event.timestamp || "event"}-${index}`
                    }
                  >
                    <div className="full-timeline-line">
                      <span />
                    </div>

                    <div className="full-timeline-body">
                      <div className="full-timeline-top">
                        <div>
                          <strong>
                            {event.operation ||
                              event.event_type ||
                              "Security event"}
                          </strong>

                          {event.attack_stage && (
                            <Badge variant="neutral" size="small">
                              {label(event.attack_stage)}
                            </Badge>
                          )}
                        </div>

                        <time dateTime={event.timestamp}>{formatDate(event.timestamp)}</time>
                      </div>

                      <div className="full-timeline-meta">
                        <span>
                          Destination: <strong>{getTarget(event) === 'honeypot' ? 'Deception' : label(getTarget(event))}</strong>
                        </span>

                        {typeof event.risk_score === "number" && (
                          <span>
                            Risk: <strong>{event.risk_score}</strong>
                          </span>
                        )}

                        {event.routing_decision && (
                          <span>
                            Routing:{" "}
                            <strong>
                              {label(event.routing_decision)}
                            </strong>
                          </span>
                        )}
                      </div>

                      {(typeof event.success === 'boolean' || Object.keys(event.synthetic_exposure_counts || {}).length > 0) && <div className="timeline-outcome">
                        {typeof event.success === 'boolean' && <StatusPill status={event.success ? 'observed' : 'failed'} size="small" dot={false} />}
                        {Object.entries(event.synthetic_exposure_counts || {}).map(([entity, count]) => <span key={entity}>{count} synthetic {label(entity)}</span>)}
                      </div>}
                      {event.routing_reason && (
                        <p>{event.routing_reason}</p>
                      )}

                      {event.reasons &&
                        event.reasons.length > 0 && (
                          <div className="timeline-reasons">
                            {event.reasons.map((reason, reasonIndex) => (
                              <span key={`${reason}-${reasonIndex}`}>
                                {reason}
                              </span>
                            ))}
                          </div>
                        )}

                      {event.triggered_rules &&
                        event.triggered_rules.length > 0 && (
                          <div className="timeline-rules">
                            {event.triggered_rules.map((rule) => (
                              <Badge
                                key={rule}
                                variant="warning"
                                size="small"
                              >
                                {label(rule)}
                              </Badge>
                            ))}
                          </div>
                        )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="incident-card">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">DETECTION ENGINE</p>
                <h2>Triggered rules</h2>
              </div>
            </div>

            {incident.triggered_rules &&
            incident.triggered_rules.length > 0 ? (
              <div className="incident-chip-list">
                {incident.triggered_rules.map((rule) => (
                  <Badge key={rule} variant="warning">
                    {label(rule)}
                  </Badge>
                ))}
              </div>
            ) : (
              <div className="incident-empty-inline">
                No triggered rules were attached to the incident.
              </div>
            )}
          </section>

          <section className="incident-card">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">OBSERVED OPERATIONS</p>
                <h2>Operations</h2>
              </div>
            </div>

            {incident.operations_observed &&
            incident.operations_observed.length > 0 ? (
              <div className="operation-list">
                {incident.operations_observed.map(
                  (operation, index) => (
                    <div key={`${operation}-${index}`}>
                      <span>{index + 1}</span>
                      <code>{operation}</code>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <div className="incident-empty-inline">
                No operation list is attached to this incident.
              </div>
            )}
          </section>
        </div>

        <aside className="incident-side-column">
          <section className="incident-card">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">ROUTING</p>
                <h2>Protection decisions</h2>
              </div>
            </div>

            {incident.routing_decisions &&
            incident.routing_decisions.length > 0 ? (
              <div className="routing-decision-list">
                {incident.routing_decisions.map(
                  (decision, index) => (
                    <div key={`${decision}-${index}`}>
                      <span>{index + 1}</span>
                      <strong>{decision === 'honeypot' ? 'Isolated deception' : label(decision)}</strong>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <p className="muted-copy">
                No routing decisions were attached to this record.
              </p>
            )}
          </section>

          <section className="incident-card">
            <div className="incident-card-heading">
              <div>
                <p className="eyebrow">ADVISORY ANALYSIS</p>
                <h2>Incident analysis</h2>
              </div>

              {incident.analysis?.analysis_provider && (
                <span className="analysis-source">
                  {incident.analysis.analysis_provider}
                </span>
              )}
            </div>

            {!incident.analysis ? (
              <div className="analysis-not-generated">
                <div className="analysis-symbol">✦</div>

                <h3>Analysis not generated</h3>

                <p>
                  Run the incident analysis pipeline to produce an
                  advisory investigation report from sanitized
                  session telemetry.
                </p>

                {incident.session_id && (
                  <Button
                    variant="secondary"
                    onClick={() => void runAnalysis()}
                    disabled={analysisLoading}
                  >
                    {analysisLoading
                      ? "Analyzing…"
                      : "Generate analysis"}
                  </Button>
                )}
              </div>
            ) : (
              <div className="full-analysis">
                {incident.analysis.incident_summary && (
                  <div className="analysis-section">
                    <span>Incident summary</span>
                    <p>{incident.analysis.incident_summary}</p>
                  </div>
                )}

                {incident.analysis.observed_behavior && (
                  <div className="analysis-section">
                    <span>Observed behavior</span>
                    <p>{incident.analysis.observed_behavior}</p>
                  </div>
                )}

                {incident.analysis.risk_assessment && (
                  <div className="analysis-section">
                    <span>Risk assessment</span>
                    <p>{incident.analysis.risk_assessment}</p>
                  </div>
                )}

                {incident.analysis.likely_objective && (
                  <div className="analysis-section">
                    <span>Likely objective · advisory inference</span>
                    <p>{incident.analysis.likely_objective}</p>
                  </div>
                )}

                {incident.analysis.attack_stage_progression &&
                  incident.analysis.attack_stage_progression.length >
                    0 && (
                    <div className="analysis-section">
                      <span>Stage progression</span>

                      <div className="stage-progression">
                        {incident.analysis.attack_stage_progression.map(
                          (stage, index) => (
                            <div key={`${stage}-${index}`}>
                              <span>{index + 1}</span>
                              <strong>{label(stage)}</strong>
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                  )}

                {incident.analysis.sensitive_resources_targeted &&
                  incident.analysis.sensitive_resources_targeted
                    .length > 0 && (
                    <div className="analysis-section">
                      <span>Sensitive resources targeted</span>

                      <div className="analysis-tag-list">
                        {incident.analysis.sensitive_resources_targeted.map(
                          (resource) => (
                            <Badge
                              key={resource}
                              variant="info"
                              size="small"
                            >
                              {resource}
                            </Badge>
                          ),
                        )}
                      </div>
                    </div>
                  )}

                {incident.analysis.exposed_synthetic_entities &&
                  Object.keys(
                    incident.analysis.exposed_synthetic_entities,
                  ).length > 0 && (
                    <div className="analysis-section">
                      <span>Exposed synthetic entities</span>

                      <div className="entity-count-list">
                        {Object.entries(
                          incident.analysis
                            .exposed_synthetic_entities,
                        ).map(([entity, count]) => (
                          <div key={entity}>
                            <span>{entity}</span>
                            <strong>{count}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {incident.analysis.suspicious_patterns &&
                  incident.analysis.suspicious_patterns.length >
                    0 && (
                    <div className="analysis-section">
                      <span>Suspicious patterns</span>

                      <div className="pattern-list">
                        {incident.analysis.suspicious_patterns.map(
                          (pattern, index) => (
                            <div
                              key={`${pattern.pattern_name || "pattern"}-${index}`}
                            >
                              <strong>
                                {pattern.pattern_name ||
                                  "Suspicious pattern"}
                              </strong>

                              {pattern.description && (
                                <p>{pattern.description}</p>
                              )}

                              {pattern.confidence && (
                                <Badge
                                  variant="neutral"
                                  size="small"
                                >
                                  {label(pattern.confidence)}
                                </Badge>
                              )}
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                  )}

                {incident.analysis.defensive_recommendations &&
                  incident.analysis.defensive_recommendations
                    .length > 0 && (
                    <div className="analysis-section">
                      <span>Defensive recommendations</span>

                      <div className="recommendation-list">
                        {incident.analysis.defensive_recommendations.map(
                          (recommendation, index) => (
                            <div
                              className="recommendation-item"
                              key={`${recommendation.action_type || "action"}-${index}`}
                            >
                              <div>
                                <strong>
                                  {label(
                                    recommendation.action_type ||
                                      "defensive action",
                                  )}
                                </strong>

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

                              <p>
                                {recommendation.description ||
                                  "No description provided."}
                              </p>
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                  )}

                {incident.analysis.limitations && (
                  <div className="analysis-limitations">
                    <strong>Analysis limitations</strong>
                    <p>{incident.analysis.limitations}</p>
                  </div>
                )}
              </div>
            )}
          </section>

          <section className="incident-card incident-advisory-card">
            <p className="eyebrow">CONTROL BOUNDARY</p>
            <h3>AI remains advisory</h3>
            <p>
              PhantomLayer's deterministic detection, risk scoring,
              and routing engines remain authoritative. AI analysis
              is used to help security teams understand observed
              behavior and prioritize investigation.
            </p>
          </section>
        </aside>
      </section>
    </div>
  );
}