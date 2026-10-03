import { Link } from "react-router-dom";

import { AgentStatusCard } from "../../components/AgentStatusCard";
import { Badge } from "../../components/Badge";
import { StatusPill } from "../../components/StatusPill";

import { useOrganization } from "../../hooks/useOrganization";

function formatDate(
  value?: string | null,
): string {
  if (!value) {
    return "Never";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return date.toLocaleString();
}

export function Agent() {
  const {
    connectedAgent,
    agents,
    verifiedDomain,
    activeProtection,
    isLoading,
    refresh,
  } = useOrganization();

  const agent =
    connectedAgent ??
    agents.find(a => a.domain_id === verifiedDomain?.id) ??
    null;

  if (isLoading) {
    return (
      <div className="customer-agent-page">
        <div className="customer-page-loading">
          <div className="customer-loading-orb">
            ⬡
          </div>

          <strong>
            Loading agent status...
          </strong>

          <span>
            Checking your infrastructure connector.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="customer-agent-page">
      {/* HEADER */}

      <section className="customer-page-header">
        <div>
          <span className="customer-eyebrow">
            INFRASTRUCTURE CONNECTOR
          </span>

          <h1>
            PhantomLayer Agent
          </h1>

          <p>
            The agent runs inside your infrastructure
            and securely connects your environment to
            the PhantomLayer control plane.
          </p>
        </div>

        {agent ? (
          <StatusPill
            status={agent.status}
          />
        ) : (
          <Badge variant="warning">
            NOT CONNECTED
          </Badge>
        )}
      </section>

      {/* AGENT STATUS */}

      <section className="customer-agent-main">
        <AgentStatusCard
          agent={agent}
          loading={false}
          onRefresh={refresh}
          onDeploy={() => {
            window.location.href =
              "/onboarding/agent";
          }}
        />
      </section>

      {/* CONNECTION DETAILS */}

      {agent && (
        <section className="agent-details-section">
          <div className="customer-section-heading">
            <div>
              <span className="customer-eyebrow">
                CONNECTION DETAILS
              </span>

              <h2>
                Agent telemetry
              </h2>
            </div>
          </div>

          <div className="agent-details-grid">
            <div className="agent-detail-card">
              <span>
                AGENT NAME
              </span>

              <strong>
                {agent.name}
              </strong>

              <small>
                Registered connector
              </small>
            </div>

            <div className="agent-detail-card">
              <span>
                VERSION
              </span>

              <strong>
                {agent.version}
              </strong>

              <small>
                Installed agent version
              </small>
            </div>

            <div className="agent-detail-card">
              <span>
                LAST HEARTBEAT
              </span>

              <strong>
                {formatDate(
                  agent.last_heartbeat_at,
                )}
              </strong>

              <small>
                Latest control-plane signal
              </small>
            </div>

            <div className="agent-detail-card">
              <span>
                TELEMETRY
              </span>

              <strong>
                {agent.telemetry_events_sent}
              </strong>

              <small>
                Events sent by this agent
              </small>
            </div>
          </div>
        </section>
      )}

      {/* INFRASTRUCTURE HEALTH */}

      <section className="agent-health-section">
        <div className="customer-section-heading">
          <div>
            <span className="customer-eyebrow">
              INFRASTRUCTURE HEALTH
            </span>

            <h2>
              Protected environment
            </h2>
          </div>
        </div>

        <div className="agent-health-grid">
          <div className="agent-health-card">
            <div className="agent-health-card-top">
              <span className="agent-health-icon">
                ◇
              </span>

              <Badge
                variant={
                  verifiedDomain
                    ? "success"
                    : "warning"
                }
              >
                {verifiedDomain
                  ? "VERIFIED"
                  : "UNVERIFIED"}
              </Badge>
            </div>

            <span className="agent-health-label">
              DOMAIN
            </span>

            <strong>
              {verifiedDomain?.domain ??
                "No domain configured"}
            </strong>

            <small>
              Customer domain protected by
              PhantomLayer.
            </small>
          </div>

          <div className="agent-health-card">
            <div className="agent-health-card-top">
              <span className="agent-health-icon">
                ◈
              </span>

              <Badge
                variant={
                  activeProtection?.enabled
                    ? "success"
                    : "warning"
                }
              >
                {activeProtection?.enabled
                  ? "ACTIVE"
                  : "PAUSED"}
              </Badge>
            </div>

            <span className="agent-health-label">
              PROTECTION
            </span>

            <strong>
              {activeProtection?.layer
                ? activeProtection.layer.toUpperCase()
                : "Not configured"}
            </strong>

            <small>
              Current deception protection
              layer.
            </small>
          </div>

          <div className="agent-health-card">
            <div className="agent-health-card-top">
              <span className="agent-health-icon">
                ⬡
              </span>

              <Badge
                variant={
                  agent?.real_db_reachable
                    ? "success"
                    : "danger"
                }
              >
                {agent?.real_db_reachable
                  ? "REACHABLE"
                  : "UNAVAILABLE"}
              </Badge>
            </div>

            <span className="agent-health-label">
              REAL DATABASE
            </span>

            <strong>
              Production connection
            </strong>

            <small>
              Reported directly by the local
              PhantomLayer agent.
            </small>
          </div>

          <div className="agent-health-card">
            <div className="agent-health-card-top">
              <span className="agent-health-icon">
                ◎
              </span>

              <Badge
                variant={
                  agent?.honeypot_db_reachable
                    ? "success"
                    : "danger"
                }
              >
                {agent?.honeypot_db_reachable
                  ? "REACHABLE"
                  : "UNAVAILABLE"}
              </Badge>
            </div>

            <span className="agent-health-label">
              HONEYPOT DATABASE
            </span>

            <strong>
              Deception environment
            </strong>

            <small>
              Isolated destination for suspicious
              activity.
            </small>
          </div>
        </div>
      </section>

      {/* ARCHITECTURE */}

      <section className="agent-architecture-section">
        <div className="customer-section-heading">
          <div>
            <span className="customer-eyebrow">
              DEPLOYMENT ARCHITECTURE
            </span>

            <h2>
              How the agent connects
            </h2>
          </div>
        </div>

        <div className="agent-architecture">
          <div className="agent-architecture-node">
            <span>
              PHANTOMLAYER
            </span>

            <strong>
              Control Plane
            </strong>

            <small>
              Configuration, incidents, telemetry
              and security analytics.
            </small>
          </div>

          <div className="agent-architecture-connection">
            <span>
              SECURE OUTBOUND
            </span>
            <div />
            <span>
              HEARTBEAT + TELEMETRY
            </span>
          </div>

          <div className="agent-architecture-node active">
            <span>
              CUSTOMER INFRASTRUCTURE
            </span>

            <strong>
              PhantomLayer Agent
            </strong>

            <small>
              Runs inside your environment and
              maintains local infrastructure access.
            </small>
          </div>

          <div className="agent-architecture-branches">
            <div>
              <strong>
                REAL DATABASE
              </strong>

              <small>
                Production data remains inside
                customer infrastructure.
              </small>
            </div>

            <div>
              <strong>
                HONEYPOT DATABASE
              </strong>

              <small>
                Isolated deception environment for
                suspicious sessions.
              </small>
            </div>
          </div>
        </div>
      </section>

      {/* NO AGENT */}

      {!agent && (
        <section className="agent-deploy-callout">
          <div>
            <span>
              AGENT REQUIRED
            </span>

            <h2>
              Connect your infrastructure
            </h2>

            <p>
              Deploy the PhantomLayer agent inside
              your environment to activate protection,
              health monitoring and telemetry.
            </p>
          </div>

          <Link
            to="/onboarding/agent"
            className="agent-deploy-link"
          >
            Deploy agent →
          </Link>
        </section>
      )}
    </div>
  );
}
