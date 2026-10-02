import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatusPill } from "../../components/StatusPill";
import { useOrganization } from "../../hooks/useOrganization";

export function Activation() {
  const navigate = useNavigate();

  const {
    verifiedDomain,
    activeProtection,
    protections,
    connectedAgent,
    refresh,
    isLoading,
    error,
  } = useOrganization();

  const [checking, setChecking] = useState(false);
  const [seconds, setSeconds] = useState(0);

  const agentConnected =
    connectedAgent?.status === "healthy" ||
    connectedAgent?.status === "degraded";

  const protectionActive =
    activeProtection?.enabled === true &&
    activeProtection.status === "active";

  const configuredProtection = protections.find(p => p.domain_id === verifiedDomain?.id);
  const protectionConfiguration =
    configuredProtection?.configuration as
      | Record<string, unknown>
      | undefined;

  const riskThreshold =
    typeof protectionConfiguration?.risk_threshold ===
    "number"
      ? protectionConfiguration.risk_threshold
      : null;

  useEffect(() => {
    if (agentConnected && protectionActive) {
      return;
    }

    const interval = window.setInterval(() => {
      setSeconds((value) => value + 1);
      void refresh();
    }, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [
    agentConnected,
    protectionActive,
    refresh,
  ]);

  async function handleRefresh() {
    setChecking(true);

    try {
      await refresh();
    } finally {
      setChecking(false);
    }
  }

  function handleDashboard() {
    navigate("/dashboard");
  }

  const ready =
    Boolean(verifiedDomain) &&
    Boolean(activeProtection) &&
    Boolean(connectedAgent) &&
    agentConnected &&
    protectionActive;

  return (
    <div className="onboarding-page activation-page">
      <div className="onboarding-page-header">
        <span className="onboarding-eyebrow">
          STEP 06 / ACTIVATION
        </span>

        <h1>
          Your security layer
          <br />
          <span>is coming online.</span>
        </h1>

        <p>
          PhantomLayer is checking your domain,
          protection configuration and agent connection.
        </p>
      </div>

      <section className="activation-status-card">
        <div
          className={[
            "activation-orb",
            ready ? "activation-orb-ready" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <div className="activation-orb-ring activation-orb-ring-one" />
          <div className="activation-orb-ring activation-orb-ring-two" />

          <div className="activation-orb-core">
            {ready ? "✓" : "P"}
          </div>
        </div>

        <span className="activation-status-label">
          {ready
            ? "PROTECTION ACTIVE"
            : "ACTIVATION IN PROGRESS"}
        </span>

        <h2>
          {ready
            ? "PhantomLayer is protecting your infrastructure."
            : "Waiting for your agent to connect."}
        </h2>

        <p>
          {ready
            ? "Your deployment is connected to the PhantomLayer control plane and ready to receive security telemetry."
            : "Keep the PhantomLayer agent running inside your infrastructure. This page will automatically check for the connection."}
        </p>

        {!ready && (
          <div className="activation-checking">
            <span className="onboarding-spinner" />

            <span>
              Checking agent health
              {seconds > 0 ? ` • ${seconds}s` : ""}
            </span>
          </div>
        )}
      </section>

      <div className="activation-grid">
        <section className="activation-checks">
          <div className="activation-section-heading">
            <span className="onboarding-eyebrow">
              DEPLOYMENT STATUS
            </span>

            <h2>Security checks</h2>
          </div>

          <div className="activation-check-list">
            <div className="activation-check">
              <div className="activation-check-icon">
                {verifiedDomain ? "✓" : "○"}
              </div>

              <div className="activation-check-copy">
                <strong>Domain verified</strong>

                <span>
                  {verifiedDomain?.domain ??
                    "Waiting for domain"}
                </span>
              </div>

              <StatusPill
                status={
                  verifiedDomain
                    ? "verified"
                    : "pending"
                }
              />
            </div>

            <div className="activation-check">
              <div className="activation-check-icon">
                {configuredProtection ? "✓" : "○"}
              </div>

              <div className="activation-check-copy">
                <strong>
                  Protection configured
                </strong>

                <span>
                  {configuredProtection?.layer
                    ? configuredProtection.layer.toUpperCase()
                    : "Waiting for configuration"}
                </span>
              </div>

              <StatusPill
                status={
                  configuredProtection?.status ??
                  "configuring"
                }
              />
            </div>

            <div className="activation-check">
              <div className="activation-check-icon">
                {agentConnected ? "✓" : "○"}
              </div>

              <div className="activation-check-copy">
                <strong>Agent connected</strong>

                <span>
                  {connectedAgent?.name ??
                    "Waiting for agent"}
                </span>
              </div>

              <StatusPill
                status={
                  connectedAgent?.status ??
                  "pending"
                }
              />
            </div>

            <div className="activation-check">
              <div className="activation-check-icon">
                {connectedAgent?.real_db_reachable
                  ? "✓"
                  : "○"}
              </div>

              <div className="activation-check-copy">
                <strong>
                  Production database
                </strong>

                <span>
                  {connectedAgent?.real_db_reachable
                    ? "Reachable through agent"
                    : "Waiting for agent health"}
                </span>
              </div>

              <StatusPill
                status={
                  connectedAgent?.real_db_reachable
                    ? "connected"
                    : "disconnected"
                }
              />
            </div>

            <div className="activation-check">
              <div className="activation-check-icon">
                {connectedAgent?.honeypot_db_reachable
                  ? "✓"
                  : "○"}
              </div>

              <div className="activation-check-copy">
                <strong>
                  Honeypot database
                </strong>

                <span>
                  {connectedAgent?.honeypot_db_reachable
                    ? "Deception layer reachable"
                    : "Waiting for agent health"}
                </span>
              </div>

              <StatusPill
                status={
                  connectedAgent?.honeypot_db_reachable
                    ? "connected"
                    : "disconnected"
                }
              />
            </div>
          </div>
        </section>

        <aside className="activation-summary">
          <span className="onboarding-eyebrow">
            PROTECTION SUMMARY
          </span>

          <div className="activation-summary-domain">
            <span>DOMAIN</span>

            <strong>
              {verifiedDomain?.domain ??
                "Not configured"}
            </strong>
          </div>

          <div className="activation-summary-row">
            <span>PROTECTION</span>

            <strong>
              {configuredProtection?.layer
                ? configuredProtection.layer.toUpperCase()
                : "—"}
            </strong>
          </div>

          <div className="activation-summary-row">
            <span>CONFIGURED REFERENCE</span>

            <strong>{riskThreshold == null ? 'Integration policy' : `${riskThreshold} (metadata)`}</strong>
          </div>

          <div className="activation-summary-row">
            <span>AGENT</span>

            <strong>
              {connectedAgent?.version ?? "Waiting"}
            </strong>
          </div>

          <div className="activation-summary-divider" />

          <div className="activation-security-note">
            <span>◈</span>

            <p>
              Suspicious activity can be evaluated by
              PhantomLayer and routed to isolated
              deception infrastructure without requiring
              your production data to leave your
              environment.
            </p>
          </div>
        </aside>
      </div>

      {(error || isLoading) && !ready && (
        <div className="activation-info">
          {error ? (
            <>
              <span>!</span>
              <p>{error}</p>
            </>
          ) : (
            <>
              <span>◌</span>
              <p>
                Synchronizing deployment status with the
                PhantomLayer control plane...
              </p>
            </>
          )}
        </div>
      )}

      <div className="activation-actions">
        <button
          type="button"
          className="onboarding-secondary-button"
          onClick={handleRefresh}
          disabled={checking}
        >
          {checking ? (
            <>
              <span className="onboarding-spinner" />
              Checking...
            </>
          ) : (
            <>↻ Check again</>
          )}
        </button>

        <button
          type="button"
          className="onboarding-primary-button"
          onClick={handleDashboard}
          disabled={!ready}
        >
          Open security dashboard
          <span>→</span>
        </button>
      </div>

      {!ready && (
        <p className="activation-help">
          The dashboard will become available once the
          agent reports a healthy connection.
        </p>
      )}
    </div>
  );
}