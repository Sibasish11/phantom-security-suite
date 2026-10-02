import { useEffect, useMemo, useState } from "react";
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";
import { getAgents } from "../../lib/api";
import type { Agent } from "../../types/agent";

function formatDate(value?: string | null) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function statusVariant(status: Agent["status"]) {
  switch (status) {
    case "healthy":
      return "success" as const;
    case "degraded":
      return "warning" as const;
    case "offline":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

function statusLabel(status: Agent["status"]) {
  switch (status) {
    case "healthy":
      return "Healthy";
    case "degraded":
      return "Degraded";
    case "offline":
      return "Offline";
    case "pending":
      return "Pending";
    default:
      return status;
  }
}

function connectivityLabel(
  value: boolean | null | undefined,
) {
  if (value === true) return "Reachable";
  if (value === false) return "Unavailable";
  return "Unknown";
}

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] =
    useState<Agent | null>(null);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadAgents(showRefreshing = false) {
    if (showRefreshing) {
      setRefreshing(true);
    }

    try {
      setError("");

      const response = await getAgents();

      setAgents(response);

      setSelectedAgent((current) => {
        if (!current) return null;

        return (
          response.find(
            (agent) =>
              agent.agent_id === current.agent_id,
          ) || null
        );
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load agents.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadAgents();

    const interval = window.setInterval(() => {
      void loadAgents();
    }, 15000);

    return () => window.clearInterval(interval);
  }, []);

  const filteredAgents = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return agents;
    }

    return agents.filter((agent) =>
      [
        agent.name,
        agent.agent_id,
        agent.version,
        agent.status,
        agent.domain_id,
        ...(agent.capabilities || []),
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query),
        ),
    );
  }, [agents, search]);

  const healthyCount = agents.filter(
    (agent) => agent.status === "healthy",
  ).length;

  const degradedCount = agents.filter(
    (agent) => agent.status === "degraded",
  ).length;

  const offlineCount = agents.filter(
    (agent) => agent.status === "offline",
  ).length;

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="admin-agents-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">CONTROL PLANE</p>

          <h1>Agent Registry</h1>

          <p>
            Infrastructure agents reporting health and
            telemetry to PhantomLayer.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() => void loadAgents(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>Agent registry unavailable</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="admin-agent-summary">
        <div>
          <span>Total agents</span>
          <strong>{agents.length}</strong>
        </div>

        <div>
          <span>Healthy</span>
          <strong className="admin-positive">
            {healthyCount}
          </strong>
        </div>

        <div>
          <span>Degraded</span>
          <strong className="admin-warning">
            {degradedCount}
          </strong>
        </div>

        <div>
          <span>Offline</span>
          <strong className="admin-danger">
            {offlineCount}
          </strong>
        </div>
      </section>

      <section className="admin-data-card">
        <div className="admin-data-header">
          <div>
            <p className="eyebrow">DEPLOYED INFRASTRUCTURE</p>
            <h2>Connected agents</h2>
          </div>

          <div className="admin-search">
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search agents…"
              aria-label="Search agents"
            />
          </div>
        </div>

        {filteredAgents.length === 0 ? (
          <EmptyState
            title={
              search
                ? "No matching agents"
                : "No agents registered"
            }
            description={
              search
                ? "Try searching by agent name, version, capability, or ID."
                : "Agents registered through the PhantomLayer deployment flow will appear here."
            }
          />
        ) : (
          <div className="admin-agent-table-wrap">
            <ResponsiveTable className="admin-agent-table">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Connectivity</th>
                  <th>Telemetry</th>
                  <th>Last heartbeat</th>
                </tr>
              </thead>

              <tbody>
                {filteredAgents.map((agent) => (
                  <tr
                    key={agent.agent_id}
                    className={
                      selectedAgent?.agent_id ===
                      agent.agent_id
                        ? "admin-agent-row-selected"
                        : ""
                    }
                    onClick={() =>
                      setSelectedAgent(agent)
                    }
                  >
                    <td>
                      <div className="admin-agent-name">
                        <div className="admin-agent-avatar">
                          {agent.name
                            .charAt(0)
                            .toUpperCase()}
                        </div>

                        <div>
                          <strong>{agent.name}</strong>

                          <span>
                            {agent.domain_id
                              ? "Domain attached"
                              : "No domain attached"}
                          </span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <Badge
                        variant={statusVariant(
                          agent.status,
                        )}
                        size="small"
                      >
                        {statusLabel(agent.status)}
                      </Badge>
                    </td>

                    <td>
                      <code>{agent.version}</code>
                    </td>

                    <td>
                      <div className="admin-connectivity">
                        <span>
                          <i
                            className={
                              agent.real_db_reachable
                                ? "is-up"
                                : "is-down"
                            }
                          />
                          Real DB
                        </span>

                        <span>
                          <i
                            className={
                              agent.honeypot_db_reachable
                                ? "is-up"
                                : "is-down"
                            }
                          />
                          Honeypot
                        </span>
                      </div>
                    </td>

                    <td>
                      <strong>
                        {agent.telemetry_events_sent ?? 0}
                      </strong>
                    </td>

                    <td>
                      {formatDate(
                        agent.last_heartbeat_at,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </ResponsiveTable>
          </div>
        )}
      </section>

      {selectedAgent && (
        <aside className="admin-agent-detail">
          <div className="admin-agent-detail-header">
            <div>
              <p className="eyebrow">AGENT DETAILS</p>
              <h2>{selectedAgent.name}</h2>
            </div>

            <button
              className="admin-close-button"
              onClick={() =>
                setSelectedAgent(null)
              }
              aria-label="Close agent details"
            >
              ×
            </button>
          </div>

          <div className="admin-agent-status-line">
            <Badge
              variant={statusVariant(
                selectedAgent.status,
              )}
              size="small"
            >
              {statusLabel(selectedAgent.status)}
            </Badge>

            <span>
              v{selectedAgent.version}
            </span>
          </div>

          <div className="admin-agent-detail-grid">
            <div>
              <span>Agent ID</span>
              <code>{selectedAgent.agent_id}</code>
            </div>

            <div>
              <span>Domain ID</span>
              <code>
                {selectedAgent.domain_id || "—"}
              </code>
            </div>

            <div>
              <span>Registered</span>
              <strong>
                {formatDate(
                  selectedAgent.registered_at,
                )}
              </strong>
            </div>

            <div>
              <span>Last heartbeat</span>
              <strong>
                {formatDate(
                  selectedAgent.last_heartbeat_at,
                )}
              </strong>
            </div>

            <div>
              <span>Real database</span>
              <strong>
                {connectivityLabel(
                  selectedAgent.real_db_reachable,
                )}
              </strong>
            </div>

            <div>
              <span>Honeypot database</span>
              <strong>
                {connectivityLabel(
                  selectedAgent.honeypot_db_reachable,
                )}
              </strong>
            </div>
          </div>

          <div className="admin-agent-section">
            <span>CAPABILITIES</span>

            <div className="admin-capabilities">
              {selectedAgent.capabilities?.length ? (
                selectedAgent.capabilities.map(
                  (capability) => (
                    <Badge
                      key={capability}
                      variant="info"
                      size="small"
                    >
                      {capability}
                    </Badge>
                  ),
                )
              ) : (
                <span>No capabilities reported.</span>
              )}
            </div>
          </div>

          <div className="admin-agent-telemetry">
            <span>TELEMETRY EVENTS SENT</span>
            <strong>
              {selectedAgent.telemetry_events_sent ?? 0}
            </strong>
          </div>
        </aside>
      )}
    </div>
  );
}