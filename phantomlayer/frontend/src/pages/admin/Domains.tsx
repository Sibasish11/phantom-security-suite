import { useEffect, useMemo, useState } from "react";
import { Badge } from "../../components/Badge";
import { ResponsiveTable } from '../../components/ResponsiveTable';
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingScreen } from "../../components/LoadingScreen";
import { apiGet, apiPost } from "../../lib/api";

type DomainRecord = {
  id: string;
  domain: string;
  verification_record_name: string;
  verification_token: string;
  token_expires_at: string;
  verified: boolean;
  verified_at?: string | null;
};

type VerificationResponse = {
  id: string;
  domain: string;
  verified: boolean;
  verified_at?: string | null;
  detail: string;
};

function formatDate(value?: string | null) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function isExpired(value: string) {
  const date = new Date(value);

  return !Number.isNaN(date.getTime()) && date.getTime() < Date.now();
}

export function Domains() {
  const [domains, setDomains] = useState<DomainRecord[]>([]);
  const [selectedDomain, setSelectedDomain] =
    useState<DomainRecord | null>(null);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [verifyingId, setVerifyingId] = useState<string | null>(
    null,
  );

  const [error, setError] = useState("");
  const [verificationMessage, setVerificationMessage] =
    useState("");

  async function loadDomains(showRefreshing = false) {
    if (showRefreshing) {
      setRefreshing(true);
    }

    try {
      setError("");

      const response = await apiGet<DomainRecord[]>(
        "/domains",
      );

      setDomains(response);

      setSelectedDomain((current) => {
        if (!current) return null;

        return (
          response.find(
            (domain) => domain.id === current.id,
          ) || null
        );
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load domains.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function verifyDomain(domain: DomainRecord) {
    setVerifyingId(domain.id);
    setVerificationMessage("");
    setError("");

    try {
      const response =
        await apiPost<VerificationResponse>(
          `/domains/${domain.id}/verify`,
        );

      setVerificationMessage(
        `${domain.domain}: ${response.detail}`,
      );

      await loadDomains();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to verify domain.",
      );
    } finally {
      setVerifyingId(null);
    }
  }

  useEffect(() => {
    void loadDomains();

    const interval = window.setInterval(() => {
      void loadDomains();
    }, 15000);

    return () => window.clearInterval(interval);
  }, []);

  const filteredDomains = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return domains;
    }

    return domains.filter((domain) =>
      [
        domain.domain,
        domain.id,
        domain.verification_record_name,
        domain.verified ? "verified" : "pending",
      ].some((value) =>
        String(value).toLowerCase().includes(query),
      ),
    );
  }, [domains, search]);

  const verifiedCount = domains.filter(
    (domain) => domain.verified,
  ).length;

  const pendingCount = domains.filter(
    (domain) => !domain.verified,
  ).length;

  const expiredCount = domains.filter(
    (domain) =>
      !domain.verified &&
      isExpired(domain.token_expires_at),
  ).length;

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <div className="admin-domains-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">CONTROL PLANE</p>

          <h1>Domains</h1>

          <p>
            Domain ownership and verification records managed by
            PhantomLayer.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={() => void loadDomains(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </section>

      {error && (
        <div className="customer-alert customer-alert-danger">
          <strong>Domain operation failed</strong>
          <span>{error}</span>
        </div>
      )}

      {verificationMessage && (
        <div className="admin-domain-success">
          <strong>Verification response</strong>
          <span>{verificationMessage}</span>
        </div>
      )}

      <section className="admin-domain-summary">
        <div>
          <span>Total domains</span>
          <strong>{domains.length}</strong>
        </div>

        <div>
          <span>Verified</span>
          <strong className="admin-positive">
            {verifiedCount}
          </strong>
        </div>

        <div>
          <span>Pending</span>
          <strong className="admin-warning">
            {pendingCount}
          </strong>
        </div>

        <div>
          <span>Expired tokens</span>
          <strong className="admin-danger">
            {expiredCount}
          </strong>
        </div>
      </section>

      <section className="admin-data-card">
        <div className="admin-data-header">
          <div>
            <p className="eyebrow">DOMAIN REGISTRY</p>
            <h2>Customer domains</h2>
          </div>

          <div className="admin-search">
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search domains…"
              aria-label="Search domains"
            />
          </div>
        </div>

        {filteredDomains.length === 0 ? (
          <EmptyState
            title={
              search
                ? "No matching domains"
                : "No domains registered"
            }
            description={
              search
                ? "Try searching by domain name, ID, or verification record."
                : "Domains created through the PhantomLayer onboarding flow will appear here."
            }
          />
        ) : (
          <div className="admin-domain-table-wrap">
            <ResponsiveTable className="admin-domain-table">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>DNS record</th>
                  <th>Token expiry</th>
                  <th>Verified at</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredDomains.map((domain) => {
                  const expired =
                    !domain.verified &&
                    isExpired(
                      domain.token_expires_at,
                    );

                  return (
                    <tr
                      key={domain.id}
                      className={
                        selectedDomain?.id === domain.id
                          ? "admin-domain-row-selected"
                          : ""
                      }
                      onClick={() =>
                        setSelectedDomain(domain)
                      }
                    >
                      <td>
                        <div className="admin-domain-name">
                          <div className="admin-domain-icon">
                            ◉
                          </div>

                          <div>
                            <strong>
                              {domain.domain}
                            </strong>

                            <span>
                              {domain.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        {domain.verified ? (
                          <Badge
                            variant="success"
                            size="small"
                          >
                            Verified
                          </Badge>
                        ) : expired ? (
                          <Badge
                            variant="danger"
                            size="small"
                          >
                            Expired
                          </Badge>
                        ) : (
                          <Badge
                            variant="warning"
                            size="small"
                          >
                            Pending
                          </Badge>
                        )}
                      </td>

                      <td>
                        <code>
                          {domain.verification_record_name}
                        </code>
                      </td>

                      <td>
                        <span
                          className={
                            expired
                              ? "admin-expired-date"
                              : ""
                          }
                        >
                          {formatDate(
                            domain.token_expires_at,
                          )}
                        </span>
                      </td>

                      <td>
                        {formatDate(domain.verified_at)}
                      </td>

                      <td>
                        {!domain.verified && (
                          <Button
                            variant="secondary"
                            disabled={
                              verifyingId === domain.id
                            }
                            onClick={(event) => {
                              event.stopPropagation();
                              void verifyDomain(domain);
                            }}
                          >
                            {verifyingId === domain.id
                              ? "Checking…"
                              : "Verify"}
                          </Button>
                        )}

                        {domain.verified && (
                          <span className="admin-verified-mark">
                            ✓ Verified
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </ResponsiveTable>
          </div>
        )}
      </section>

      {selectedDomain && (
        <aside className="admin-domain-detail">
          <div className="admin-domain-detail-header">
            <div>
              <p className="eyebrow">DOMAIN DETAILS</p>

              <h2>{selectedDomain.domain}</h2>
            </div>

            <button
              className="admin-close-button"
              onClick={() =>
                setSelectedDomain(null)
              }
              aria-label="Close domain details"
            >
              ×
            </button>
          </div>

          <div className="admin-domain-status">
            {selectedDomain.verified ? (
              <Badge
                variant="success"
                size="small"
              >
                Ownership verified
              </Badge>
            ) : (
              <Badge
                variant="warning"
                size="small"
              >
                Awaiting verification
              </Badge>
            )}
          </div>

          <div className="admin-domain-detail-grid">
            <div>
              <span>Domain ID</span>
              <code>{selectedDomain.id}</code>
            </div>

            <div>
              <span>Verification record</span>
              <code>
                {selectedDomain.verification_record_name}
              </code>
            </div>

            <div>
              <span>Token expiry</span>
              <strong>
                {formatDate(
                  selectedDomain.token_expires_at,
                )}
              </strong>
            </div>

            <div>
              <span>Verified at</span>
              <strong>
                {formatDate(
                  selectedDomain.verified_at,
                )}
              </strong>
            </div>
          </div>

          <div className="admin-domain-instruction">
            <span>VERIFICATION MODEL</span>

            <p>
              PhantomLayer verifies ownership by checking the
              TXT record at:
            </p>

            <code>
              {selectedDomain.verification_record_name}
            </code>

            <p>
              The verification endpoint only marks the domain
              verified when the expected token is actually
              present in DNS.
            </p>
          </div>

          {!selectedDomain.verified && (
            <Button
              variant="secondary"
              disabled={
                verifyingId === selectedDomain.id
              }
              onClick={() =>
                void verifyDomain(selectedDomain)
              }
            >
              {verifyingId === selectedDomain.id
                ? "Checking DNS…"
                : "Check DNS verification"}
            </Button>
          )}
        </aside>
      )}
    </div>
  );
}