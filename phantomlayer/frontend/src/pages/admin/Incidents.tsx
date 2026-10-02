import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, getIncident } from "../../lib/api";
import { Link } from 'react-router-dom';
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { DetailDrawer } from '../../components/DetailDrawer';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";

type Severity = "critical" | "high" | "medium" | "low" | string;
type Status =
  | "open"
  | "investigating"
  | "resolved"
  | "closed"
  | string;

interface Incident {
  id: string;
  session_id?: string;
  title: string;
  summary?: string;
  severity: Severity;
  status: Status;
  attack_stage?: string;
  risk_score?: number;
  confidence?: number;
  source?: string;
  first_seen_at?: string;
  last_seen_at?: string;
  created_at: string;
  updated_at?: string;
  triggered_rules?: string[];
  recommendations?: string[];
  organization_id?: string;
  domain_id?: string;
}

function formatDate(value?: string) {
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

function statusVariant(status: Status) {
  switch (status.toLowerCase()) {
    case "open":
      return "danger" as const;

    case "investigating":
      return "warning" as const;

    case "resolved":
    case "closed":
      return "success" as const;

    default:
      return "neutral" as const;
  }
}

function shortId(value?: string) {
  if (!value) return "—";

  if (value.length <= 18) {
    return value;
  }

  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

export function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");

  const [selectedIncident, setSelectedIncident] =
    useState<Incident | null>(null);

  const [detailError, setDetailError] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  async function openIncident(incident: Incident) {
    setSelectedIncident(incident); setDetailError(''); setDetailLoading(true);
    try {
      const detail = await getIncident(incident.id) as unknown as Record<string, unknown>;
      const analysis = detail.analysis as {incident_summary?:string; defensive_recommendations?:{description?:string}[]} | undefined;
      setSelectedIncident(current => current?.id === incident.id ? {...current,
        source: typeof detail.source === 'string' ? detail.source : current.source,
        triggered_rules: Array.isArray(detail.triggered_rules) ? detail.triggered_rules.map(String) : [],
        summary: analysis?.incident_summary || current.summary,
        recommendations: analysis?.defensive_recommendations?.map(action => action.description || '').filter(Boolean) || [],
      } : current);
    } catch (err) {setDetailError(err instanceof Error ? err.message : 'Unable to load incident evidence.');}
    finally {setDetailLoading(false);}
  }

  const loadIncidents = useCallback(async (silent = false) => {
    try {
      if (silent) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response = await apiGet<{incidents?: Record<string, unknown>[]} | Record<string, unknown>[]>("/incidents");
      const rows = Array.isArray(response) ? response : response.incidents || [];
      setIncidents(rows.map(row => ({...row,
        id: String(row.incident_id || row.id || ''),
        session_id: String(row.session_id || ''),
        title: typeof row.title === 'string' ? row.title : `${String(row.attack_stage || 'Security').replaceAll('_', ' ')} investigation`,
        summary: typeof row.summary === 'string' ? row.summary : `${row.interaction_count ?? 0} observed interactions`,
        severity: String(row.severity || 'unknown'), status: String(row.status || 'pending'),
        created_at: String(row.created_at || ''), risk_score: typeof row.risk_score === 'number' ? row.risk_score : undefined,
      })));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load incidents.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadIncidents();
  }, [loadIncidents]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadIncidents(true);
    }, 15000);

    return () => window.clearInterval(interval);
  }, [loadIncidents]);

  const filteredIncidents = useMemo(() => {
    const query = search.trim().toLowerCase();

    return incidents.filter((incident) => {
      const matchesSeverity =
        severity === "all" ||
        incident.severity.toLowerCase() === severity;

      const matchesStatus =
        status === "all" ||
        incident.status.toLowerCase() === status;

      if (!matchesSeverity || !matchesStatus) {
        return false;
      }

      if (!query) {
        return true;
      }

      const searchable = [
        incident.id,
        incident.session_id,
        incident.title,
        incident.summary,
        incident.severity,
        incident.status,
        incident.attack_stage,
        incident.source,
        incident.organization_id,
        incident.domain_id,
        ...(incident.triggered_rules || []),
      ]
        .join(" ")
        .toLowerCase();

      return searchable.includes(query);
    });
  }, [incidents, search, severity, status]);

  const stats = useMemo(() => {
    return {
      total: incidents.length,

      critical: incidents.filter(
        (incident) =>
          incident.severity.toLowerCase() === "critical",
      ).length,

      high: incidents.filter(
        (incident) =>
          incident.severity.toLowerCase() === "high",
      ).length,

      active: incidents.filter((incident) => {
        const value = incident.status.toLowerCase();

        return value === 'pending' || value === 'failed';
      }).length,

      resolved: incidents.filter((incident) => {
        const value = incident.status.toLowerCase();

        return value === 'completed';
      }).length,
    };
  }, [incidents]);

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="module-page">
      <section className="module-title">
        <div>
          <p className="eyebrow">INCIDENT RESPONSE</p>

          <h1>Security incidents</h1>

          <p className="module-description">
            Centralized incident view generated from PhantomLayer
            security telemetry and attack-session analysis.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() => void loadIncidents(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="alert alert-danger">
          <strong>Unable to load incidents.</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="metrics-grid">
        <article className="metric-card cyan">
          <div className="metric-icon">Σ</div>

          <div className="metric-copy">
            <span>TOTAL INCIDENTS</span>
            <strong>{stats.total}</strong>
            <small>Recorded incidents</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-icon">C</div>

          <div className="metric-copy">
            <span>CRITICAL</span>
            <strong>{stats.critical}</strong>
            <small>Critical severity</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-icon">H</div>

          <div className="metric-copy">
            <span>HIGH</span>
            <strong>{stats.high}</strong>
            <small>High severity</small>
          </div>
        </article>

        <article className="metric-card amber">
          <div className="metric-icon">!</div>

          <div className="metric-copy">
            <span>PENDING ANALYSIS</span>
            <strong>{stats.active}</strong>
            <small>Pending or awaiting retry</small>
          </div>
        </article>

        <article className="metric-card green">
          <div className="metric-icon">✓</div>

          <div className="metric-copy">
            <span>ANALYZED</span>
            <strong>{stats.resolved}</strong>
            <small>Completed advisory reports</small>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Incident Registry</h2>
          </div>

          <div className="live-indicator">
            <span />
            LIVE INCIDENTS
          </div>
        </div>

        <div className="table-toolbar">
          <input
            className="input"
            placeholder="Search incidents, sessions, rules…"
            aria-label="Search incident registry"
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />

          <select
            className="input"
            value={severity}
            aria-label="Filter incident severity"
            onChange={(event) =>
              setSeverity(event.target.value)
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
            value={status}
            aria-label="Filter analysis state"
            onChange={(event) =>
              setStatus(event.target.value)
            }
          >
            <option value="all">All analysis states</option>
            {Array.from(new Set(incidents.map(incident => incident.status.toLowerCase()))).map(value => <option key={value} value={value}>{value === 'completed' ? 'Analyzed' : value.charAt(0).toUpperCase() + value.slice(1)}</option>)}
          </select>
        </div>

        <div className="table-scroll">
          {filteredIncidents.length === 0 ? (
            <EmptyState
              title="No incidents found"
              description={
                incidents.length === 0
                  ? "PhantomLayer has not generated any incidents yet."
                  : "Try changing the current search or filters."
              }
            />
          ) : (
            <ResponsiveTable>
              <thead>
                <tr>
                  <th>CREATED</th>
                  <th>INCIDENT</th>
                  <th>SEVERITY</th>
                  <th>STATUS</th>
                  <th>STAGE</th>
                  <th>RISK</th>
                  <th>SESSION</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {filteredIncidents.map((incident) => (
                  <tr
                    key={incident.id}
                    onClick={() => void openIncident(incident)}
                  >
                    <td>
                      {formatDate(incident.created_at)}
                    </td>

                    <td>
                      <strong>
                        {incident.title ||
                          "Security Incident"}
                      </strong>

                      {incident.summary && (
                        <>
                          <br />
                          <small>
                            {incident.summary.slice(0, 90)}
                            {incident.summary.length > 90
                              ? "…"
                              : ""}
                          </small>
                        </>
                      )}
                    </td>

                    <td>
                      <Badge
                        variant={severityVariant(
                          incident.severity,
                        )}
                        size="small"
                      >
                        {incident.severity}
                      </Badge>
                    </td>

                    <td>
                      <Badge
                        variant={statusVariant(
                          incident.status,
                        )}
                        size="small"
                      >
                        {incident.status}
                      </Badge>
                    </td>

                    <td>
                      {incident.attack_stage || "—"}
                    </td>

                    <td>
                      <strong>
                        {incident.risk_score ?? "—"}
                      </strong>
                    </td>

                    <td>
                      <code>
                        {shortId(incident.session_id)}
                      </code>
                    </td>

                    <td>
                      <Button
                        variant="ghost"
                        onClick={(event) => {
                          event.stopPropagation();
                          void openIncident(incident);
                        }}
                      >
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </ResponsiveTable>
          )}
        </div>
      </section>

      {selectedIncident && (
        <DetailDrawer label="Incident details" onClose={() => setSelectedIncident(null)}>
          <aside
            className="incident-drawer"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <button
              className="drawer-close"
              onClick={() =>
                setSelectedIncident(null)
              }
              aria-label="Close incident details"
            >
              ×
            </button>

            <p className="eyebrow">
              INCIDENT DETAIL
            </p>

            <h2>
              {selectedIncident.title ||
                "Security Incident"}
            </h2>

            <Link className="text-link" to={`/dashboard/incidents/${selectedIncident.id}`}>Open full investigation →</Link>
            {detailLoading && <p className="drawer-copy" role="status">Loading incident evidence…</p>}
            {detailError && <div className="ui-alert ui-alert-error" role="alert">{detailError}</div>}
            <div className="drawer-meta">
              <Badge
                variant={severityVariant(
                  selectedIncident.severity,
                )}
                size="small"
              >
                {selectedIncident.severity}
              </Badge>

              <Badge
                variant={statusVariant(
                  selectedIncident.status,
                )}
                size="small"
              >
                {selectedIncident.status}
              </Badge>
            </div>

            <div className="drawer-risk">
              <div className="risk-circle">
                <strong>
                  {selectedIncident.risk_score ?? "—"}
                </strong>

                <span>RISK</span>
              </div>

              <div>
                <small>CONFIDENCE</small>

                <strong>
                  {selectedIncident.confidence != null
                    ? `${selectedIncident.confidence}%`
                    : "—"}
                </strong>
              </div>
            </div>

            {selectedIncident.summary && (
              <section>
                <div className="drawer-label">
                  SUMMARY
                </div>

                <p className="drawer-copy">
                  {selectedIncident.summary}
                </p>
              </section>
            )}

            <section>
              <div className="drawer-label">
                IDENTIFIERS
              </div>

              <code className="session-code">
                Incident: {selectedIncident.id}
                {"\n"}
                Session:{" "}
                {selectedIncident.session_id || "—"}
                {"\n"}
                Organization:{" "}
                {selectedIncident.organization_id ||
                  "—"}
                {"\n"}
                Domain:{" "}
                {selectedIncident.domain_id || "—"}
              </code>
            </section>

            <section>
              <div className="drawer-label">
                ATTACK STAGE
              </div>

              <div className="drawer-copy">
                {selectedIncident.attack_stage ||
                  "Unknown"}
              </div>
            </section>

            <section>
              <div className="drawer-label">
                SOURCE
              </div>

              <div className="drawer-copy">
                {selectedIncident.source || "—"}
              </div>
            </section>

            <section>
              <div className="drawer-label">
                TRIGGERED RULES
              </div>

              {selectedIncident.triggered_rules
                ?.length ? (
                <div className="operation-chips">
                  {selectedIncident.triggered_rules.map(
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

            {selectedIncident.recommendations
              ?.length ? (
              <section>
                <div className="drawer-label">
                  RECOMMENDATIONS
                </div>

                <div className="recommendations">
                  {selectedIncident.recommendations.map(
                    (recommendation, index) => (
                      <div
                        className="recommendation"
                        key={`${recommendation}-${index}`}
                      >
                        <span>›</span>
                        {recommendation}
                      </div>
                    ),
                  )}
                </div>
              </section>
            ) : null}

            <section>
              <div className="drawer-label">
                TIMELINE
              </div>

              <div className="drawer-copy">
                First seen:{" "}
                {formatDate(
                  selectedIncident.first_seen_at,
                )}

                <br />

                Last seen:{" "}
                {formatDate(
                  selectedIncident.last_seen_at,
                )}

                <br />

                Created:{" "}
                {formatDate(
                  selectedIncident.created_at,
                )}

                <br />

                Updated:{" "}
                {formatDate(
                  selectedIncident.updated_at,
                )}
              </div>
            </section>
          </aside>
        </DetailDrawer>
      )}
    </div>
  );
}