import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { StatusPill } from "../../components/StatusPill";
import { useAuth } from "../../hooks/useAuth";
import { useOrganization } from "../../hooks/useOrganization";
import { getSession } from "../../lib/auth";
import { getStoredOrganization } from "../../lib/storage";

function label(value?: string) {
  return (value || "unknown").replaceAll("_", " ");
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatLayer(value?: string) {
  switch (value) {
    case "api":
      return "API protection";
    case "database":
      return "Database protection";
    case "internal":
      return "Internal deception";
    case "full":
      return "Full protection";
    default:
      return label(value);
  }
}

export function Settings() {
  const { logout } = useAuth();

  const {
    verifiedDomain,
    activeProtection,
    connectedAgent,
    error,
    isLoading: loading,
  } = useOrganization();

  const session = getSession();
  const user = session?.user;

  const storedOrganization =
    getStoredOrganization() as unknown as Record<
      string,
      unknown
    > | null;

  const organizationName =
    typeof storedOrganization?.organization_name === "string"
      ? storedOrganization.organization_name
      : typeof storedOrganization?.name === "string"
        ? storedOrganization.name
        : "Your Organization";

  const organizationId =
    typeof storedOrganization?.organization_id === "string"
      ? storedOrganization.organization_id
      : typeof storedOrganization?.id === "string"
        ? storedOrganization.id
        : "Unavailable";

  const agent = connectedAgent as unknown as Record<
    string,
    unknown
  > | null;

  const protection =
    activeProtection as unknown as Record<
      string,
      unknown
    > | null;

  const domain =
    verifiedDomain as unknown as Record<
      string,
      unknown
    > | null;

  return (
    <div className="customer-settings-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">CONTROL CENTER</p>

          <h1>Settings</h1>

          <p>
            Manage your PhantomLayer organization, connected
            infrastructure, and security deployment state.
          </p>
        </div>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>Organization data unavailable</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="settings-grid">
        <div className="settings-main">

          {/* ORGANIZATION */}

          <section className="settings-card">
            <div className="settings-card-heading">
              <div>
                <p className="eyebrow">ORGANIZATION</p>
                <h2>Organization profile</h2>
              </div>

              <Badge variant="success" size="small">
                Active
              </Badge>
            </div>

            <div className="settings-fields">
              <div className="settings-field">
                <span>Organization</span>

                <strong>{organizationName}</strong>
              </div>

              <div className="settings-field">
                <span>Organization ID</span>

                <code>{organizationId}</code>
              </div>

              <div className="settings-field">
                <span>Your role</span>

                <strong className="settings-capitalize">
                  {label(user?.role)}
                </strong>
              </div>

              <div className="settings-field">
                <span>Account email</span>

                <strong>
                  {user?.email || "Unavailable"}
                </strong>
              </div>
            </div>
          </section>

          {/* DOMAIN */}

          <section className="settings-card">
            <div className="settings-card-heading">
              <div>
                <p className="eyebrow">DOMAIN</p>
                <h2>Verified domain</h2>
              </div>

              {domain ? (
                <Badge variant="success" size="small">
                  Verified
                </Badge>
              ) : (
                <Badge variant="warning" size="small">
                  Not verified
                </Badge>
              )}
            </div>

            {loading ? (
              <div className="settings-loading">
                Loading domain configuration…
              </div>
            ) : domain ? (
              <div className="settings-resource">
                <div className="settings-resource-icon">
                  ◎
                </div>

                <div>
                  <strong>
                    {typeof domain.domain === "string"
                      ? domain.domain
                      : "Verified domain"}
                  </strong>

                  <span>
                    Verified{" "}
                    {formatDate(
                      typeof domain.verified_at === "string"
                        ? domain.verified_at
                        : null,
                    )}
                  </span>
                </div>
              </div>
            ) : (
              <div className="settings-empty">
                <strong>No verified domain</strong>

                <p>
                  Verify a domain before deploying a
                  PhantomLayer protection layer.
                </p>

                <Link to="/onboarding/domain">
                  Configure domain →
                </Link>
              </div>
            )}
          </section>

          {/* PROTECTION */}

          <section className="settings-card">
            <div className="settings-card-heading">
              <div>
                <p className="eyebrow">PROTECTION</p>
                <h2>Security deployment</h2>
              </div>

              {protection && (
                <StatusPill
                  status={
                    typeof protection.status === "string"
                      ? protection.status
                      : "unknown"
                  }
                />
              )}
            </div>

            {loading ? (
              <div className="settings-loading">
                Loading protection configuration…
              </div>
            ) : protection ? (
              <>
                <div className="settings-protection-header">
                  <div>
                    <strong>
                      {formatLayer(
                        typeof protection.layer === "string"
                          ? protection.layer
                          : undefined,
                      )}
                    </strong>

                    <span>
                      {protection.enabled === true
                        ? "Protection is enabled"
                        : "Protection is disabled"}
                    </span>
                  </div>

                  <span
                    className={
                      protection.enabled === true
                        ? "settings-state active"
                        : "settings-state paused"
                    }
                  >
                    {protection.enabled === true
                      ? "ACTIVE"
                      : "PAUSED"}
                  </span>
                </div>

                <div className="settings-fields">
                  <div className="settings-field">
                    <span>Protection ID</span>

                    <code>
                      {typeof protection.protection_id ===
                      "string"
                        ? protection.protection_id
                        : typeof protection.id === "string"
                          ? protection.id
                          : "Unavailable"}
                    </code>
                  </div>

                  <div className="settings-field">
                    <span>Configured threshold (metadata)</span>

                    <strong>
                      {protection.configuration &&
                      typeof protection.configuration ===
                        "object" &&
                      "risk_threshold" in
                        protection.configuration
                        ? String(
                            (
                              protection.configuration as Record<
                                string,
                                unknown
                              >
                            ).risk_threshold,
                          )
                        : "Default"}
                    </strong>
                  </div>

                  <div className="settings-field">
                    <span>Mode</span>

                    <strong>
                      {protection.configuration &&
                      typeof protection.configuration ===
                        "object" &&
                      "mode" in protection.configuration
                        ? label(
                            String(
                              (
                                protection.configuration as Record<
                                  string,
                                  unknown
                                >
                              ).mode,
                            ),
                          )
                        : "Deception"}
                    </strong>
                  </div>
                </div>

                <Link
                  className="settings-inline-link"
                  to="/dashboard/protection"
                >
                  Open protection settings →
                </Link>
              </>
            ) : (
              <div className="settings-empty">
                <strong>
                  No protection layer configured
                </strong>

                <p>
                  Select a PhantomLayer protection layer to
                  begin deployment.
                </p>

                <Link to="/onboarding/protection">
                  Configure protection →
                </Link>
              </div>
            )}
          </section>

          {/* AGENT */}

          <section className="settings-card">
            <div className="settings-card-heading">
              <div>
                <p className="eyebrow">AGENT</p>
                <h2>Infrastructure connection</h2>
              </div>

              {agent && (
                <StatusPill
                  status={
                    typeof agent.status === "string"
                      ? agent.status
                      : "unknown"
                  }
                />
              )}
            </div>

            {loading ? (
              <div className="settings-loading">
                Loading agent connection…
              </div>
            ) : agent ? (
              <>
                <div className="settings-resource">
                  <div className="settings-resource-icon">
                    ⌁
                  </div>

                  <div>
                    <strong>
                      {typeof agent.name === "string"
                        ? agent.name
                        : "PhantomLayer Agent"}
                    </strong>

                    <span>
                      Version{" "}
                      {typeof agent.version === "string"
                        ? agent.version
                        : "unknown"}
                      {" · "}
                      Last heartbeat{" "}
                      {formatDate(
                        typeof agent.last_heartbeat_at ===
                          "string"
                          ? agent.last_heartbeat_at
                          : null,
                      )}
                    </span>
                  </div>
                </div>

                <div className="settings-agent-grid">
                  <div>
                    <span>Status</span>

                    <strong className="settings-capitalize">
                      {label(
                        typeof agent.status === "string"
                          ? agent.status
                          : undefined,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Agent ID</span>

                    <code>
                      {typeof agent.agent_id === "string"
                        ? agent.agent_id
                        : "Unavailable"}
                    </code>
                  </div>

                  <div>
                    <span>Telemetry events</span>

                    <strong>
                      {typeof agent.telemetry_events_sent ===
                      "number"
                        ? agent.telemetry_events_sent
                        : 0}
                    </strong>
                  </div>

                  <div>
                    <span>Database connectivity</span>

                    <strong>
                      {agent.real_db_reachable === true &&
                      agent.honeypot_db_reachable === true
                        ? "Healthy"
                        : "Check connection"}
                    </strong>
                  </div>
                </div>

                <Link
                  className="settings-inline-link"
                  to="/dashboard/agent"
                >
                  Open agent details →
                </Link>
              </>
            ) : (
              <div className="settings-empty">
                <strong>No agent connected</strong>

                <p>
                  Deploy the PhantomLayer Agent inside your
                  infrastructure to activate protection.
                </p>

                <Link to="/dashboard/agent">
                  View agent deployment →
                </Link>
              </div>
            )}
          </section>
        </div>

        {/* RIGHT SIDE */}

        <aside className="settings-side">

          {/* ACCOUNT */}

          <section className="settings-card settings-account-card">
            <p className="eyebrow">ACCOUNT</p>

            <div className="account-avatar">
              {(user?.full_name || user?.email || "U")
                .charAt(0)
                .toUpperCase()}
            </div>

            <h2>
              {user?.full_name || "Administrator"}
            </h2>

            <p className="account-email">
              {user?.email || "No email available"}
            </p>

            <div className="account-role">
              <span>Role</span>

              <Badge variant="purple" size="small">
                {label(user?.role)}
              </Badge>
            </div>

            <div className="account-security">
              <div>
                <span>Authentication</span>
                <strong>Session active</strong>
              </div>

              <div>
                <span>Tenant access</span>
                <strong>Organization scoped</strong>
              </div>
            </div>

            <Button
              variant="danger"
              onClick={() => logout()}
            >
              Sign out
            </Button>
          </section>

          {/* SECURITY MODEL */}

          <section className="settings-card settings-security-card">
            <p className="eyebrow">SECURITY MODEL</p>

            <h3>
              How PhantomLayer protects your data
            </h3>

            <ul>
              <li>
                Production database credentials remain
                inside your infrastructure.
              </li>

              <li>
                The PhantomLayer Agent establishes outbound
                communication with the control plane.
              </li>

              <li>
                Suspicious traffic can be routed to isolated
                deception resources.
              </li>

              <li>
                AI analysis operates on sanitized security
                telemetry.
              </li>
            </ul>

            <Link to="/how-it-works">
              Learn how PhantomLayer works →
            </Link>
          </section>
        </aside>
      </section>
    </div>
  );
}