import type { Agent } from "../types/agent";
import { StatusPill } from "./StatusPill";

interface AgentStatusCardProps {
  agent: Agent | null;
  loading?: boolean;
  onDeploy?: () => void;
  onRefresh?: () => void;
}

interface HealthItemProps {
  label: string;
  healthy: boolean | null;
}

function HealthItem({
  label,
  healthy,
}: HealthItemProps) {
  return (
    <div className="agent-health-item">
      <span
        className={[
          "agent-health-icon",
          healthy == null ? 'agent-health-pending' : healthy
            ? "agent-health-ok"
            : "agent-health-bad",
        ].join(" ")}
      >
        {healthy == null ? '—' : healthy ? "✓" : "×"}
      </span>

      <span>{label}</span>
    </div>
  );
}

export function AgentStatusCard({
  agent,
  loading = false,
  onDeploy,
  onRefresh,
}: AgentStatusCardProps) {
  if (loading) {
    return (
      <section className="agent-status-card">
        <div className="agent-card-header">
          <div>
            <div className="agent-card-kicker">
              PHANTOMLAYER AGENT
            </div>

            <div className="agent-skeleton-title" />
          </div>
        </div>

        <div className="agent-skeleton-status" />

        <div className="agent-health-grid">
          <div className="agent-skeleton-row" />
          <div className="agent-skeleton-row" />
          <div className="agent-skeleton-row" />
        </div>
      </section>
    );
  }

  if (!agent) {
    return (
      <section className="agent-status-card agent-status-empty">
        <div className="agent-card-header">
          <div>
            <div className="agent-card-kicker">
              PHANTOMLAYER AGENT
            </div>

            <h3>Deploy your protection agent</h3>
          </div>

          <div className="agent-orb agent-orb-idle">
            P
          </div>
        </div>

        <p className="agent-card-description">
          Your protection agent runs inside your
          infrastructure and securely connects back to
          PhantomLayer. Your production database stays
          inside your environment.
        </p>

        {onDeploy && (
          <button
            type="button"
            className="agent-deploy-button"
            onClick={onDeploy}
          >
            Deploy agent
            <span>→</span>
          </button>
        )}
      </section>
    );
  }

  const isHealthy =
    agent.status === "healthy";

  const isConnected =
    agent.status === "healthy" ||
    agent.status === "degraded";

  return (
    <section className="agent-status-card">
      <div className="agent-card-header">
        <div>
          <div className="agent-card-kicker">
            PHANTOMLAYER AGENT
          </div>

          <h3>{agent.name}</h3>

          <span className="agent-version">
            v{agent.version}
          </span>
        </div>

        <div
          className={[
            "agent-orb",
            isHealthy
              ? "agent-orb-healthy"
              : "agent-orb-warning",
          ].join(" ")}
        >
          P
        </div>
      </div>

      <div className="agent-status-main">
        <StatusPill
          status={agent.status}
          size="medium"
        />

        <span className="agent-status-message">
          {isHealthy
            ? "Protection agent is connected and healthy."
            : isConnected
              ? "Agent is connected but needs attention."
              : "Agent is not currently connected."}
        </span>
      </div>

      <div className="agent-health-grid">
        <HealthItem
          label="Agent heartbeat"
          healthy={isConnected}
        />

        <HealthItem
          label="Real database"
          healthy={agent.last_heartbeat_at ? agent.real_db_reachable : null}
        />

        <HealthItem
          label="Honeypot database"
          healthy={agent.last_heartbeat_at ? agent.honeypot_db_reachable : null}
        />

        <HealthItem
          label="Agent event batches"
          healthy={agent.telemetry_events_sent > 0 ? true : null}
        />
      </div>

      <p className="agent-counter-note">Last-reported health. Integration observations may be recorded separately in the event console.</p>
      <div className="agent-card-footer">
        <div className="agent-meta">
          <span>
            Last heartbeat
          </span>

          <strong>
            {agent.last_heartbeat_at
              ? new Date(
                  agent.last_heartbeat_at,
                ).toLocaleString()
              : "Never"}
          </strong>
        </div>

        <div className="agent-meta">
          <span>
            Agent events sent
          </span>

          <strong>
            {agent.telemetry_events_sent.toLocaleString()}
          </strong>
        </div>

        {onRefresh && (
          <button
            type="button"
            className="agent-refresh-button"
            onClick={onRefresh}
          >
            Refresh
          </button>
        )}
      </div>
    </section>
  );
}