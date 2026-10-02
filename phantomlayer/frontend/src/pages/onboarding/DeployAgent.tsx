import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AgentStatusCard } from "../../components/AgentStatusCard";
import { LoadingScreen } from '../../components/LoadingScreen';
import { CopyCommand } from "../../components/CopyCommand";
import { useOrganization } from "../../hooks/useOrganization";
import { registerAgent } from "../../lib/api";

export function DeployAgent() {
  const navigate = useNavigate();

  const {
    verifiedDomain,
    protections,
    connectedAgent,
    agents,
    refresh,
    isLoading,
    error,
  } = useOrganization();

  const [registering, setRegistering] = useState(false);
  const [registrationError, setRegistrationError] =
    useState("");

  const [agentId, setAgentId] = useState("");
  const [registrationToken, setRegistrationToken] =
    useState("");

  const existingAgent =
    connectedAgent ?? agents[0] ?? null;

  const busy = isLoading || registering;
  // Configuration precedes the heartbeat; ACTIVE must not be required to
  // register the very agent that makes the protection active.
  const configuredProtection = protections.find(p => p.domain_id === verifiedDomain?.id && p.enabled);

  const installCommand = useMemo(() => {
    if (!agentId || !registrationToken) {
      return "";
    }

    return [
      "PHANTOMLAYER_URL=http://localhost:8000",
      `AGENT_ID=${agentId}`,
      `REGISTRATION_TOKEN=${registrationToken}`,
      "python -m phantomlayer_agent.main",
    ].join(" \\\n");
  }, [agentId, registrationToken]);

  async function handleRegisterAgent() {
    setRegistrationError("");

    if (!verifiedDomain) {
      navigate("/onboarding/domain");
      return;
    }

    if (!configuredProtection) {
      navigate("/onboarding/protection");
      return;
    }

    const domainData =
      verifiedDomain as unknown as Record<
        string,
        unknown
      >;

    const domainId =
      typeof domainData.id === "string"
        ? domainData.id
        : "";

    if (!domainId) {
      setRegistrationError(
        "The verified domain ID could not be found.",
      );
      return;
    }

    setRegistering(true);

    try {
      const result = await registerAgent({
        name: "PhantomLayer Agent",
        domain_id: domainId,
        version: "1.0.0",
        capabilities: [
          "api_protection",
          "database_deception",
          "telemetry",
        ],
      });

      setAgentId(result.agent_id);
      setRegistrationToken(
        result.registration_token,
      );

      await refresh();
    } catch (err) {
      setRegistrationError(
        err instanceof Error
          ? err.message
          : "Unable to register the agent.",
      );
    } finally {
      setRegistering(false);
    }
  }

  async function handleRefresh() {
    await refresh();
  }

  function handleContinue() {
    navigate("/onboarding/activation");
  }

  if (isLoading) return <LoadingScreen message="Loading agent deployment…" />;

  if (!verifiedDomain) {
    return (
      <div className="onboarding-page">
        <section className="onboarding-card">
          <span className="onboarding-eyebrow">
            STEP 05 / AGENT
          </span>

          <h1>
            Domain setup
            <br />
            <span>is required.</span>
          </h1>

          <p>
            Connect and verify your domain before
            deploying the PhantomLayer agent.
          </p>

          <button
            type="button"
            className="onboarding-primary-button"
            onClick={() =>
              navigate("/onboarding/domain")
            }
          >
            Go to domain setup
            <span>→</span>
          </button>
        </section>
      </div>
    );
  }

  if (!configuredProtection) {
    return (
      <div className="onboarding-page">
        <section className="onboarding-card">
          <span className="onboarding-eyebrow">
            STEP 05 / AGENT
          </span>

          <h1>
            Choose a
            <br />
            <span>protection layer.</span>
          </h1>

          <p>
            Configure protection before deploying an
            agent into your infrastructure.
          </p>

          <button
            type="button"
            className="onboarding-primary-button"
            onClick={() =>
              navigate("/onboarding/protection")
            }
          >
            Choose protection
            <span>→</span>
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-page-header">
        <span className="onboarding-eyebrow">
          STEP 05 / AGENT
        </span>

        <h1>
          Deploy your
          <br />
          <span>PhantomLayer agent.</span>
        </h1>

        <p>
          The agent runs inside your infrastructure and
          connects outbound to the PhantomLayer control
          plane.
        </p>
      </div>

      <div className="agent-deployment-layout">
        <section className="onboarding-card">
          <div className="onboarding-card-header">
            <div className="onboarding-card-icon">
              ⬡
            </div>

            <div>
              <span>PHANTOMLAYER AGENT</span>
              <h2>Deployment</h2>
            </div>
          </div>

          {existingAgent ? (
            <AgentStatusCard
              agent={existingAgent}
              loading={busy}
              onRefresh={handleRefresh}
            />
          ) : (
            <>
              <div className="agent-deployment-intro">
                <span>01</span>

                <div>
                  <strong>
                    Register an agent
                  </strong>

                  <p>
                    PhantomLayer creates an agent identity
                    and one-time registration credential
                    for your organization.
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="onboarding-primary-button"
                onClick={handleRegisterAgent}
                disabled={busy}
              >
                {registering ? (
                  <>
                    <span className="onboarding-spinner" />
                    Registering agent...
                  </>
                ) : (
                  <>
                    Register agent
                    <span>→</span>
                  </>
                )}
              </button>
            </>
          )}

          {(registrationError || error) && (
            <div
              className="onboarding-error"
              role="alert"
            >
              <span>!</span>

              <p>
                {registrationError || error}
              </p>
            </div>
          )}

          {registrationToken && (
            <div className="agent-registration-result">
              <div className="agent-registration-warning">
                <span>!</span>

                <div>
                  <strong>
                    Save this token now
                  </strong>

                  <p>
                    The registration token is a secret.
                    Store it securely and don't expose it
                    in source control.
                  </p>
                </div>
              </div>

              <div className="agent-credential">
                <span>AGENT ID</span>

                <CopyCommand
                  command={agentId}
                  label="Copy agent ID"
                />
              </div>

              <div className="agent-credential">
                <span>REGISTRATION TOKEN</span>

                <CopyCommand
                  command={registrationToken}
                  label="Copy token"
                />
              </div>

              {installCommand && (
                <div className="agent-credential">
                  <span>LOCAL AGENT COMMAND</span>

                  <CopyCommand
                    command={installCommand}
                    label="Copy command"
                  />
                </div>
              )}
            </div>
          )}
        </section>

        <aside className="onboarding-info-panel">
          <span className="onboarding-eyebrow">
            ARCHITECTURE
          </span>

          <div className="agent-architecture">
            <div className="agent-architecture-cloud">
              <span>PHANTOMLAYER</span>
              <strong>CONTROL PLANE</strong>
            </div>

            <div className="agent-architecture-link">
              <span />
              <small>SECURE OUTBOUND</small>
              <span />
            </div>

            <div className="agent-architecture-node">
              <span>⬡</span>

              <div>
                <small>
                  CUSTOMER INFRASTRUCTURE
                </small>

                <strong>
                  PhantomLayer Agent
                </strong>
              </div>
            </div>

            <div className="agent-architecture-targets">
              <div>
                <span>REAL DB</span>
                <strong>Production</strong>
              </div>

              <div>
                <span>HONEYPOT</span>
                <strong>Deception</strong>
              </div>
            </div>
          </div>

          <div className="onboarding-security-note">
            <span>◈</span>

            <div>
              <strong>
                Your credentials stay local.
              </strong>

              <p>
                Production database credentials remain
                inside your infrastructure. The
                PhantomLayer cloud does not need a copy
                of your production database.
              </p>
            </div>
          </div>
        </aside>
      </div>

      <div className="protection-selection-actions">
        <button
          type="button"
          className="onboarding-secondary-button"
          onClick={() =>
            navigate("/onboarding/protection")
          }
          disabled={busy}
        >
          ← Back
        </button>

        <button
          type="button"
          className="onboarding-primary-button"
          onClick={handleContinue}
          disabled={!existingAgent || busy}
        >
          Check activation
          <span>→</span>
        </button>
      </div>
    </div>
  );
}