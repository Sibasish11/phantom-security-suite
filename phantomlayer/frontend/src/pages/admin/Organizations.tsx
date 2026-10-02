import { useEffect, useMemo, useState } from "react";
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";
import { apiGet } from "../../lib/api";

type Organization = {
  organization_id?: string;
  id?: string;
  name: string;
  slug?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
};

type OrganizationResponse = {
  organizations?: Organization[];
  items?: Organization[];
  results?: Organization[];
};

function formatDate(value?: string) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function normalizeOrganizations(
  payload: unknown,
): Organization[] {
  if (Array.isArray(payload)) {
    return payload as Organization[];
  }

  if (!payload || typeof payload !== "object") {
    return [];
  }

  const response = payload as OrganizationResponse;

  return (
    response.organizations ||
    response.items ||
    response.results ||
    []
  );
}

function statusVariant(status?: string) {
  switch ((status || "").toLowerCase()) {
    case "active":
      return "success" as const;
    case "suspended":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

export function Organizations() {
  const [organizations, setOrganizations] = useState<
    Organization[]
  >([]);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadOrganizations(
    showLoading = false,
  ) {
    if (showLoading) {
      setRefreshing(true);
    }

    try {
      setError("");

      /*
       * The current control-plane API is tenant-scoped.
       * This page therefore consumes whatever organization
       * collection the authenticated provider endpoint exposes.
       */
      const response = await apiGet<unknown>("/organizations");

      setOrganizations(normalizeOrganizations(response));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load organizations.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadOrganizations();

    const interval = window.setInterval(() => {
      void loadOrganizations();
    }, 15000);

    return () => window.clearInterval(interval);
  }, []);

  const filteredOrganizations = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return organizations;
    }

    return organizations.filter((organization) =>
      [
        organization.name,
        organization.slug,
        organization.organization_id,
        organization.id,
        organization.status,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query),
        ),
    );
  }, [organizations, search]);

  const activeCount = organizations.filter(
    (organization) =>
      organization.status?.toLowerCase() === "active",
  ).length;

  const suspendedCount = organizations.filter(
    (organization) =>
      organization.status?.toLowerCase() === "suspended",
  ).length;

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="admin-organizations-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">ORGANIZATION ADMINISTRATION</p>

          <h1>Organizations</h1>

          <p>
            Your authenticated organization. Organization administrators do not
            have access to other customers or platform-wide data.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() => void loadOrganizations(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>Organization feed unavailable</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="admin-org-summary">
        <div>
          <span>Total organizations</span>
          <strong>{organizations.length}</strong>
        </div>

        <div>
          <span>Active</span>
          <strong className="admin-positive">
            {activeCount}
          </strong>
        </div>

        <div>
          <span>Suspended</span>
          <strong className="admin-danger">
            {suspendedCount}
          </strong>
        </div>
      </section>

      <section className="admin-data-card">
        <div className="admin-data-header">
          <div>
            <p className="eyebrow">TENANT DIRECTORY</p>
            <h2>Customer organizations</h2>
          </div>

          <div className="admin-search">
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search organizations…"
              aria-label="Search organizations"
            />
          </div>
        </div>

        {filteredOrganizations.length === 0 ? (
          <EmptyState
            title={
              search
                ? "No matching organizations"
                : "No organizations available"
            }
            description={
              search
                ? "Try a different organization name, slug, or ID."
                : "No organization records are currently available to this control-plane session."
            }
          />
        ) : (
          <div className="admin-org-table-wrap">
            <ResponsiveTable className="admin-org-table">
              <thead>
                <tr>
                  <th>Organization</th>
                  <th>Slug</th>
                  <th>Status</th>
                  <th>Organization ID</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {filteredOrganizations.map(
                  (organization) => {
                    const id =
                      organization.organization_id ||
                      organization.id ||
                      "—";

                    return (
                      <tr key={id}>
                        <td>
                          <div className="admin-org-name">
                            <div className="admin-org-avatar">
                              {organization.name
                                .charAt(0)
                                .toUpperCase()}
                            </div>

                            <div>
                              <strong>
                                {organization.name}
                              </strong>

                              <span>
                                Customer tenant
                              </span>
                            </div>
                          </div>
                        </td>

                        <td>
                          <code>
                            {organization.slug || "—"}
                          </code>
                        </td>

                        <td>
                          <Badge
                            variant={statusVariant(
                              organization.status,
                            )}
                            size="small"
                          >
                            {organization.status ||
                              "unknown"}
                          </Badge>
                        </td>

                        <td>
                          <code className="admin-id">
                            {id}
                          </code>
                        </td>

                        <td>
                          <span className="admin-date">
                            {formatDate(
                              organization.created_at,
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </ResponsiveTable>
          </div>
        )}
      </section>

      <section className="admin-org-note">
        <div className="admin-org-note-icon">i</div>

        <div>
          <strong>Your organization, not a global tenant directory</strong>

          <p>
            This directory is scoped to your authenticated organization.
            Suspension, deletion, and membership management are not available
            in this demonstration.
          </p>
        </div>
      </section>
    </div>
  );
}