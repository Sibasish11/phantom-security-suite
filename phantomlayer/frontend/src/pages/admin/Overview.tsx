import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet } from "../../lib/api";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { StatusPill } from '../../components/StatusPill';

type Stats = {
  total_incidents: number;
  critical_incidents: number;
  high_risk_incidents: number;
  active_honeypot_sessions: number;
  active_honeypots: number;
  honeypot_interactions: number;
  requests_routed_to_honeypot: number;
  requests_routed_to_real: number;
  blocked_requests: number;
  attack_stages: Record<string, number>;
  top_triggered_rules: Array<{
    rule: string;
    count: number;
  }>;
};

type Incident = {
  id?: string;
  incident_id?: string;
  session_id?: string;
  title?: string;
  summary?: string;
  severity?: string;
  status?: string;
  attack_stage?: string;
  risk_score?: number;
  created_at?: string;
  first_seen_at?: string;
  last_seen_at?: string;
};

type SecurityEvent = {
  event_id: string;
  session_id?: string;
  timestamp: string;
  event_type: string;
  operation?: string;
  final_target?: string;
  risk_score?: number;
  severity?: string;
};

type Domain = {
  id: string;
  domain: string;
  verified?: boolean;
  status?: string;
};

type Agent = {
  agent_id: string;
  name: string;
  status: string;
  version: string;
  last_heartbeat_at?: string;
  real_db_reachable?: boolean;
  honeypot_db_reachable?: boolean;
};

type Protection = {
  id: string;
  layer: string;
  status: string;
  enabled: boolean;
  domain_id?: string;
};

type DashboardData = {
  stats: Stats | null;
  incidents: Incident[];
  events: SecurityEvent[];
  domains: Domain[];
  agents: Agent[];
  protections: Protection[];
};

const EMPTY_STATS: Stats = {
  total_incidents: 0,
  critical_incidents: 0,
  high_risk_incidents: 0,
  active_honeypot_sessions: 0,
  active_honeypots: 0,
  honeypot_interactions: 0,
  requests_routed_to_honeypot: 0,
  requests_routed_to_real: 0,
  blocked_requests: 0,
  attack_stages: {},
  top_triggered_rules: [],
};

const EMPTY_DATA: DashboardData = {
  stats: null,
  incidents: [],
  events: [],
  domains: [],
  agents: [],
  protections: [],
};

function extractList<T>(
  value: unknown,
  keys: string[],
): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (!value || typeof value !== "object") {
    return [];
  }

  const object = value as Record<string, unknown>;

  for (const key of keys) {
    if (Array.isArray(object[key])) {
      return object[key] as T[];
    }
  }

  return [];
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

function formatNumber(value?: number): string {
  return new Intl.NumberFormat("en-IN").format(value ?? 0);
}

function formatTime(value?: string): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusBadge({value}: {value?: string}) {
  return <StatusPill status={value || 'unknown'} size="small" dot={false} />;
}

export function Overview() {
  const navigate = useNavigate();

  const [data, setData] =
    useState<DashboardData>(EMPTY_DATA);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [warning, setWarning] = useState("");

  const loadDashboard = useCallback(async () => {
    setRefreshing(true);

    const results = await Promise.allSettled([
      apiGet<Stats>("/security/stats"),
      apiGet<unknown>("/incidents"),
      apiGet<unknown>("/security/events/recent"),
      apiGet<unknown>("/domains"),
      apiGet<unknown>("/agents"),
      apiGet<unknown>("/protections"),
    ]);

    const next: DashboardData = {
      stats: data.stats,
      incidents: data.incidents,
      events: data.events,
      domains: data.domains,
      agents: data.agents,
      protections: data.protections,
    };

    const warnings: string[] = [];

    if (results[0].status === "fulfilled") {
      next.stats = results[0].value;
    } else {
      warnings.push("security stats");
    }

    if (results[1].status === "fulfilled") {
      next.incidents = extractList<Incident>(
        results[1].value,
        ["incidents", "items", "results"],
      );
    } else {
      warnings.push("incidents");
    }

    if (results[2].status === "fulfilled") {
      next.events = extractList<SecurityEvent>(
        results[2].value,
        ["events", "items", "results"],
      );
    } else {
      warnings.push("security events");
    }

    if (results[3].status === "fulfilled") {
      next.domains = extractList<Domain>(
        results[3].value,
        ["domains", "items", "results"],
      );
    } else {
      warnings.push("domains");
    }

    if (results[4].status === "fulfilled") {
      next.agents = extractList<Agent>(
        results[4].value,
        ["agents", "items", "results"],
      );
    } else {
      warnings.push("agents");
    }

    if (results[5].status === "fulfilled") {
      next.protections = extractList<Protection>(
        results[5].value,
        ["protections", "items", "results"],
      );
    } else {
      warnings.push("protections");
    }

    setData(next);

    if (warnings.length > 0) {
      setWarning(
        `Unavailable: ${warnings.join(", ")}.`,
      );
    } else {
      setWarning("");
    }

    setLoading(false);
    setRefreshing(false);
  }, [data]);

  useEffect(() => {
    void loadDashboard();

    const interval = window.setInterval(() => {
      void loadDashboard();
    }, 15000);

    return () => {
      window.clearInterval(interval);
    };
  }, [loadDashboard]);

  const stats = data.stats ?? EMPTY_STATS;

  const recentIncidents = useMemo(() => {
    return [...data.incidents]
      .sort((a, b) => {
        const aTime = new Date(
          a.last_seen_at ??
            a.first_seen_at ??
            a.created_at ??
            "",
        ).getTime();

        const bTime = new Date(
          b.last_seen_at ??
            b.first_seen_at ??
            b.created_at ??
            "",
        ).getTime();

        return bTime - aTime;
      })
      .slice(0, 6);
  }, [data.incidents]);

  const recentEvents = useMemo(() => {
    return [...data.events]
      .sort(
        (a, b) =>
          new Date(b.timestamp).getTime() -
          new Date(a.timestamp).getTime(),
      )
      .slice(0, 7);
  }, [data.events]);

  const healthyAgents = data.agents.filter(
    (agent) => agent.status === "healthy",
  ).length;

  const verifiedDomains = data.domains.filter(
    (domain) =>
      domain.verified === true ||
      domain.status === "verified",
  ).length;

  const activeProtections =
    data.protections.filter(
      (protection) =>
        protection.enabled &&
        protection.status === "active",
    ).length;

  const totalTraffic =
    stats.requests_routed_to_real +
    stats.requests_routed_to_honeypot +
    stats.blocked_requests;

  const realPercentage =
    totalTraffic > 0
      ? (stats.requests_routed_to_real /
          totalTraffic) *
        100
      : 0;

  const honeypotPercentage =
    totalTraffic > 0
      ? (stats.requests_routed_to_honeypot /
          totalTraffic) *
        100
      : 0;

  const blockedPercentage =
    totalTraffic > 0
      ? (stats.blocked_requests / totalTraffic) *
        100
      : 0;

  const stageEntries = Object.entries(
    stats.attack_stages,
  ).sort((a, b) => b[1] - a[1]);

  const maxStageCount =
    stageEntries.length > 0
      ? Math.max(...stageEntries.map((entry) => entry[1]))
      : 1;

  if (loading) {
    return (
      <div className="module-page">
        <div className="panel admin-loading-panel">
          <div className="eyebrow">
            PHANTOMLAYER CONTROL PLANE
          </div>

          <h2>Loading organization telemetry…</h2>

          <p>
            Collecting security, infrastructure and
            deployment state.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="module-page admin-overview">
      <div className="module-title">
        <div>
          <div className="eyebrow">
            PHANTOMLAYER CONTROL PLANE
          </div>

          <h1>Organization overview</h1>

          <p>
            Security telemetry and infrastructure
            status for your authenticated organization.
          </p>
        </div>

        <div className="admin-overview-actions">
          <span className="admin-system-status">
            <i
              className={
                warning
                  ? "warning"
                  : ""
              }
            />

            {warning
              ? "PARTIAL TELEMETRY"
              : "CONTROL PLANE NOMINAL"}
          </span>

          <button
            type="button"
            className="admin-refresh-button"
            onClick={() => void loadDashboard()}
            disabled={refreshing}
          >
            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>
        </div>
      </div>

      {warning && (
        <div className="admin-overview-warning">
          <strong>Telemetry warning</strong>
          <span>{warning}</span>
        </div>
      )}

      <div className="metrics-grid">
        <article className="metric-card purple">
          <div className="metric-copy">
            <span>Total Incidents</span>
            <strong>
              {formatNumber(stats.total_incidents)}
            </strong>
            <small>security incidents</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-copy">
            <span>Critical</span>
            <strong>
              {formatNumber(stats.critical_incidents)}
            </strong>
            <small>critical incidents</small>
          </div>
        </article>

        <article className="metric-card red">
          <div className="metric-copy">
            <span>High Risk</span>
            <strong>
              {formatNumber(stats.high_risk_incidents)}
            </strong>
            <small>high-risk incidents</small>
          </div>
        </article>

        <article className="metric-card cyan">
          <div className="metric-copy">
            <span>Active Sessions</span>
            <strong>
              {formatNumber(
                stats.active_honeypot_sessions,
              )}
            </strong>
            <small>honeypot sessions</small>
          </div>
        </article>

        <article className="metric-card amber">
          <div className="metric-copy">
            <span>Interactions</span>
            <strong>
              {formatNumber(
                stats.honeypot_interactions,
              )}
            </strong>
            <small>deception interactions</small>
          </div>
        </article>
      </div>

      <div className="admin-overview-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                INFRASTRUCTURE
              </div>

              <h3>Environment status</h3>
            </div>

            <span className="live-indicator">
              ● POLLING 15S
            </span>
          </div>

          <div className="admin-status-grid">
            <button
              type="button"
              className="admin-status-card"
              onClick={() =>
                navigate("/admin/agents")
              }
            >
              <span className="admin-status-icon">
                ◉
              </span>

              <div>
                <span>HIVE SENTINELS</span>

                <strong>
                  {healthyAgents}/
                  {data.agents.length}
                </strong>

                <small>
                  healthy agents
                </small>
              </div>
            </button>

            <button
              type="button"
              className="admin-status-card"
              onClick={() =>
                navigate("/admin/domains")
              }
            >
              <span className="admin-status-icon">
                ◇
              </span>

              <div>
                <span>DOMAINS</span>

                <strong>
                  {verifiedDomains}/
                  {data.domains.length}
                </strong>

                <small>
                  verified domains
                </small>
              </div>
            </button>

            <button
              type="button"
              className="admin-status-card"
              onClick={() =>
                navigate("/admin/protections")
              }
            >
              <span className="admin-status-icon">
                ⬡
              </span>

              <div>
                <span>PROTECTION</span>

                <strong>
                  {activeProtections}/
                  {data.protections.length}
                </strong>

                <small>
                  active layers
                </small>
              </div>
            </button>
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                ROUTING FABRIC
              </div>

              <h3>Traffic Distribution</h3>
            </div>
          </div>

          <div className="admin-routing-total">
            <span>OBSERVED REQUESTS</span>

            <strong>
              {formatNumber(totalTraffic)}
            </strong>
          </div>

          <div className="admin-routing-bar">
            <span
              className="real"
              style={{
                width: `${realPercentage}%`,
              }}
            />

            <span
              className="honeypot"
              style={{
                width: `${honeypotPercentage}%`,
              }}
            />

            <span
              className="blocked"
              style={{
                width: `${blockedPercentage}%`,
              }}
            />
          </div>

          <div className="admin-routing-legend">
            <div>
              <i className="real" />
              <span>REAL</span>
              <strong>
                {formatNumber(
                  stats.requests_routed_to_real,
                )}
              </strong>
            </div>

            <div>
              <i className="honeypot" />
              <span>HONEYPOT</span>
              <strong>
                {formatNumber(
                  stats.requests_routed_to_honeypot,
                )}
              </strong>
            </div>

            <div>
              <i className="blocked" />
              <span>BLOCKED</span>
              <strong>
                {formatNumber(
                  stats.blocked_requests,
                )}
              </strong>
            </div>
          </div>
        </section>
      </div>

      <div className="admin-overview-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                ATTACK INTELLIGENCE
              </div>

              <h3>Attack Stages</h3>
            </div>
          </div>

          {stageEntries.length > 0 ? (
            <div className="admin-stage-list">
              {stageEntries.map(
                ([stage, count]) => (
                  <div
                    className="admin-stage-row"
                    key={stage}
                  >
                    <div>
                      <span>
                        {label(stage)}
                      </span>

                      <strong>{count}</strong>
                    </div>

                    <div className="admin-stage-track">
                      <span
                        style={{
                          width: `${
                            (count /
                              maxStageCount) *
                            100
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                ),
              )}
            </div>
          ) : (
            <div className="admin-empty">
              No attack-stage progression observed.
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                DETECTION ENGINE
              </div>

              <h3>Triggered Rules</h3>
            </div>

            <button
              type="button"
              className="admin-text-button"
              onClick={() =>
                navigate("/admin/events")
              }
            >
              View events →
            </button>
          </div>

          {stats.top_triggered_rules.length > 0 ? (
            <div className="admin-rule-list">
              {stats.top_triggered_rules
                .slice(0, 6)
                .map((rule) => (
                  <div
                    className="admin-rule-row"
                    key={rule.rule}
                  >
                    <code>{rule.rule}</code>
                    <strong>
                      {rule.count}
                    </strong>
                  </div>
                ))}
            </div>
          ) : (
            <div className="admin-empty">
              No detection rules triggered.
            </div>
          )}
        </section>
      </div>

      <div className="admin-overview-grid">
        <section className="panel table-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                INCIDENT RESPONSE
              </div>

              <h3>Recent Incidents</h3>
            </div>

            <button
              type="button"
              className="admin-text-button"
              onClick={() =>
                navigate("/admin/incidents")
              }
            >
              Open registry →
            </button>
          </div>

          <div className="table-scroll">
            <ResponsiveTable>
              <thead>
                <tr>
                  <th>INCIDENT</th>
                  <th>SEVERITY</th>
                  <th>RISK</th>
                  <th>STAGE</th>
                  <th>STATUS</th>
                  <th>TIME</th>
                </tr>
              </thead>

              <tbody>
                {recentIncidents.map(
                  (incident) => {
                    const incidentId =
                      incident.id ??
                      incident.incident_id ??
                      "";

                    return (
                      <tr
                        key={incidentId}
                        onClick={() => {
                          if (incidentId) {
                            navigate(
                              `/admin/incidents`,
                            );
                          }
                        }}
                      >
                        <td>
                          <strong>
                            {incident.title ??
                              incident.summary ??
                              incidentId.slice(
                                0,
                                8,
                              ) ??
                              "Incident"}
                          </strong>
                        </td>

                        <td>
                          <StatusBadge
                            value={
                              incident.severity
                            }
                          />
                        </td>

                        <td>
                          <span className="admin-risk-value">
                            {incident.risk_score ??
                              0}
                          </span>
                        </td>

                        <td>
                          {label(
                            incident.attack_stage,
                          )}
                        </td>

                        <td>
                          <StatusBadge
                            value={
                              incident.status
                            }
                          />
                        </td>

                        <td>
                          {formatTime(
                            incident.last_seen_at ??
                              incident.first_seen_at ??
                              incident.created_at,
                          )}
                        </td>
                      </tr>
                    );
                  },
                )}

                {!recentIncidents.length && (
                  <tr>
                    <td colSpan={6}>
                      <div className="admin-empty">
                        No incidents recorded.
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </ResponsiveTable>
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                LIVE TELEMETRY
              </div>

              <h3>Recent Events</h3>
            </div>

            <button
              type="button"
              className="admin-text-button"
              onClick={() =>
                navigate("/admin/events")
              }
            >
              Event stream →
            </button>
          </div>

          <div className="admin-event-list">
            {recentEvents.map((event) => (
              <div
                className="admin-event-row"
                key={event.event_id}
              >
                <div>
                  <strong>
                    {event.operation ??
                      event.event_type}
                  </strong>

                  <small>
                    {event.session_id ??
                      "no-session"}
                  </small>
                </div>

                <div className="admin-event-right">
                  {event.risk_score !==
                    undefined && (
                    <strong>
                      {event.risk_score}
                    </strong>
                  )}

                  <StatusBadge
                    value={
                      event.final_target
                    }
                  />
                </div>
              </div>
            ))}

            {!recentEvents.length && (
              <div className="admin-empty">
                No recent security events.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}