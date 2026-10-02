import { useEffect, useMemo, useState } from "react";
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";
import { apiGet } from "../../lib/api";

type Protection = {
  id: string;
  organization_id?: string;
  domain_id: string;
  layer: string;
  status: string;
  enabled: boolean;
  configuration?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

function formatDate(value?: string) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function layerLabel(layer: string) {
  switch (layer) {
    case "api":
      return "API Protection";
    case "database":
      return "Database Protection";
    case "internal":
      return "Internal Deception";
    case "full":
      return "Full Protection";
    default:
      return layer.replaceAll("_", " ");
  }
}

function statusVariant(status: string) {
  switch (status) {
    case "active":
      return "success" as const;
    case "paused":
      return "warning" as const;
    case "configuring":
      return "info" as const;
    default:
      return "neutral" as const;
  }
}

function configurationValue(
  configuration: Record<string, unknown> | undefined,
  key: string,
) {
  if (!configuration) return "—";

  const value = configuration[key];

  if (value === undefined || value === null) {
    return "—";
  }

  return String(value);
}

export function Protections() {
  const [protections, setProtections] = useState<
    Protection[]
  >([]);

  const [selectedProtection, setSelectedProtection] =
    useState<Protection | null>(null);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadProtections(
    showRefreshing = false,
  ) {
    if (showRefreshing) {
      setRefreshing(true);
    }

    try {
      setError("");

      const response = await apiGet<Protection[]>(
        "/protections",
      );

      setProtections(response);

      setSelectedProtection((current) => {
        if (!current) return null;

        return (
          response.find(
            (protection) =>
              protection.id === current.id,
          ) || null
        );
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load protection configurations.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadProtections();

    const interval = window.setInterval(() => {
      void loadProtections();
    }, 15000);

    return () => window.clearInterval(interval);
  }, []);

  const filteredProtections = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return protections;
    }

    return protections.filter((protection) =>
      [
        protection.id,
        protection.organization_id,
        protection.domain_id,
        protection.layer,
        protection.status,
        protection.enabled ? "enabled" : "disabled",
      ]
        .filter(Boolean)
        .some((value) =>
          String(value)
            .toLowerCase()
            .includes(query),
        ),
    );
  }, [protections, search]);

  const activeCount = protections.filter(
    (protection) =>
      protection.status === "active" &&
      protection.enabled,
  ).length;

  const configuringCount = protections.filter(
    (protection) =>
      protection.status === "configuring",
  ).length;

  const pausedCount = protections.filter(
    (protection) =>
      protection.status === "paused" ||
      !protection.enabled,
  ).length;

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="admin-protections-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">CONTROL PLANE</p>

          <h1>Protections</h1>

          <p>
            Security layers deployed across PhantomLayer
            customer infrastructure.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() =>
            void loadProtections(true)
          }
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>
            Protection registry unavailable
          </strong>
          <span>{error}</span>
        </div>
      )}

      <section className="admin-protection-summary">
        <div>
          <span>Total protections</span>
          <strong>{protections.length}</strong>
        </div>

        <div>
          <span>Active</span>
          <strong className="admin-positive">
            {activeCount}
          </strong>
        </div>

        <div>
          <span>Configuring</span>
          <strong className="admin-warning">
            {configuringCount}
          </strong>
        </div>

        <div>
          <span>Paused</span>
          <strong className="admin-danger">
            {pausedCount}
          </strong>
        </div>
      </section>

      <section className="admin-data-card">
        <div className="admin-data-header">
          <div>
            <p className="eyebrow">
              PROTECTION REGISTRY
            </p>

            <h2>Deployed security layers</h2>
          </div>

          <div className="admin-search">
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search protections…"
              aria-label="Search protections"
            />
          </div>
        </div>

        {filteredProtections.length === 0 ? (
          <EmptyState
            title={
              search
                ? "No matching protections"
                : "No protections configured"
            }
            description={
              search
                ? "Try searching by layer, status, domain ID, or protection ID."
                : "Protection configurations created during onboarding will appear here."
            }
          />
        ) : (
          <div className="admin-protection-table-wrap">
            <ResponsiveTable className="admin-protection-table">
              <thead>
                <tr>
                  <th>Protection</th>
                  <th>Layer</th>
                  <th>Status</th>
                  <th>Domain ID</th>
                  <th>Mode</th>
                  <th>Updated</th>
                </tr>
              </thead>

              <tbody>
                {filteredProtections.map(
                  (protection) => (
                    <tr
                      key={protection.id}
                      className={
                        selectedProtection?.id ===
                        protection.id
                          ? "admin-protection-row-selected"
                          : ""
                      }
                      onClick={() =>
                        setSelectedProtection(
                          protection,
                        )
                      }
                    >
                      <td>
                        <div className="admin-protection-name">
                          <div className="admin-protection-icon">
                            ◈
                          </div>

                          <div>
                            <strong>
                              {layerLabel(
                                protection.layer,
                              )}
                            </strong>

                            <span>
                              {protection.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        <Badge
                          variant="purple"
                          size="small"
                        >
                          {protection.layer}
                        </Badge>
                      </td>

                      <td>
                        <Badge
                          variant={statusVariant(
                            protection.status,
                          )}
                          size="small"
                        >
                          {protection.status}
                        </Badge>
                      </td>

                      <td>
                        <code>
                          {protection.domain_id}
                        </code>
                      </td>

                      <td>
                        <span className="admin-mode">
                          {configurationValue(
                            protection.configuration,
                            "mode",
                          )}
                        </span>
                      </td>

                      <td>
                        {formatDate(
                          protection.updated_at,
                        )}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </ResponsiveTable>
          </div>
        )}
      </section>

      {selectedProtection && (
        <aside className="admin-protection-detail">
          <div className="admin-protection-detail-header">
            <div>
              <p className="eyebrow">
                PROTECTION DETAILS
              </p>

              <h2>
                {layerLabel(
                  selectedProtection.layer,
                )}
              </h2>
            </div>

            <button
              className="admin-close-button"
              onClick={() =>
                setSelectedProtection(null)
              }
              aria-label="Close protection details"
            >
              ×
            </button>
          </div>

          <div className="admin-protection-status-line">
            <Badge
              variant={statusVariant(
                selectedProtection.status,
              )}
              size="small"
            >
              {selectedProtection.status}
            </Badge>

            <span>
              {selectedProtection.enabled
                ? "Protection enabled"
                : "Protection disabled"}
            </span>
          </div>

          <div className="admin-protection-detail-grid">
            <div>
              <span>Protection ID</span>
              <code>
                {selectedProtection.id}
              </code>
            </div>

            <div>
              <span>Organization ID</span>
              <code>
                {selectedProtection.organization_id ||
                  "—"}
              </code>
            </div>

            <div>
              <span>Domain ID</span>
              <code>
                {selectedProtection.domain_id}
              </code>
            </div>

            <div>
              <span>Created</span>
              <strong>
                {formatDate(
                  selectedProtection.created_at,
                )}
              </strong>
            </div>

            <div>
              <span>Updated</span>
              <strong>
                {formatDate(
                  selectedProtection.updated_at,
                )}
              </strong>
            </div>

            <div>
              <span>Risk threshold</span>
              <strong>
                {configurationValue(
                  selectedProtection.configuration,
                  "risk_threshold",
                )}
              </strong>
            </div>
          </div>

          <div className="admin-protection-config">
            <span>CONFIGURATION</span>

            {selectedProtection.configuration &&
            Object.keys(
              selectedProtection.configuration,
            ).length > 0 ? (
              <pre>
                {JSON.stringify(
                  selectedProtection.configuration,
                  null,
                  2,
                )}
              </pre>
            ) : (
              <p>
                No additional configuration has been
                reported.
              </p>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}