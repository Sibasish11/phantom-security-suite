import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatusPill } from "../../components/StatusPill";
import { useOrganization } from "../../hooks/useOrganization";
import { apiPost, demoVerifyDomain, verifyDomain } from "../../lib/api";
import { LoadingScreen } from '../../components/LoadingScreen';
import { CopyCommand } from '../../components/CopyCommand';

export function VerifyDomain() {
  const navigate = useNavigate();

  const {
    domains,
    verifiedDomain,
    refresh,
    isLoading,
    error,
  } = useOrganization();

  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState("");

  const domain =
    domains[0] ?? verifiedDomain;

  async function handleVerification(demo = false) {
    if (!domain) {
      navigate("/onboarding/domain");
      return;
    }

    setVerifying(true);
    setVerifyError("");

    try {
      const result = await (demo ? demoVerifyDomain(domain.id) : verifyDomain(domain.id));
      if (!result.verified) {
        setVerifyError('The DNS record has not been confirmed. Check the record and allow time for DNS propagation.');
        return;
      }
      await refresh();

      navigate("/onboarding/protection");
    } catch (err) {
      setVerifyError(
        err instanceof Error
          ? err.message
          : "Domain verification failed.",
      );
    } finally {
      setVerifying(false);
    }
  }

  if (isLoading) return <LoadingScreen message="Loading domain verification…" />;

  if (!domain) {
    return (
      <div className="onboarding-page">
        <section className="onboarding-card">
          <span className="onboarding-eyebrow">
            STEP 03 / VERIFICATION
          </span>

          <h1>
            No domain
            <br />
            <span>connected yet.</span>
          </h1>

          <p>
            Add a domain before continuing with
            verification.
          </p>

          <button
            type="button"
            className="onboarding-primary-button"
            onClick={() =>
              navigate("/onboarding/domain")
            }
          >
            Add domain
            <span>→</span>
          </button>
        </section>
      </div>
    );
  }

  if (domain.verified) {
    return (
      <div className="onboarding-page">
        <div className="onboarding-page-header">
          <span className="onboarding-eyebrow">
            STEP 03 / VERIFICATION
          </span>

          <h1>
            Domain
            <br />
            <span>verified.</span>
          </h1>

          <p>
            PhantomLayer has confirmed ownership of your
            domain. You can now choose the protection
            layer for your infrastructure.
          </p>
        </div>

        <section className="onboarding-card onboarding-card-success">
          <div className="onboarding-success-icon">
            ✓
          </div>

          <div className="onboarding-domain-preview">
            <div>
              <span>VERIFIED DOMAIN</span>
              <strong>{domain.domain}</strong>
            </div>

            <StatusPill status="verified" />
          </div>

          {domain.verified_at && (
            <p className="onboarding-muted">
              Verified successfully.
            </p>
          )}

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
          STEP 03 / VERIFICATION
        </span>

        <h1>
          Prove you
          <br />
          <span>own the domain.</span>
        </h1>

        <p>
          Add the verification record below to your DNS.
          This lets PhantomLayer confirm that the
          infrastructure belongs to your organization.
        </p>
      </div>

      <div className="onboarding-verification-layout">
        <section className="onboarding-card">
          <div className="onboarding-card-header">
            <div className="onboarding-card-icon">
              ◇
            </div>

            <div>
              <span>DOMAIN</span>
              <h2>{domain.domain}</h2>
            </div>
          </div>

          <div className="verification-record">
            <div className="verification-record-header">
              <span>DNS TXT RECORD</span>

              <span className="verification-record-status">
                PENDING
              </span>
            </div>

            <div className="verification-record-row">
              <span>NAME</span>

              <code>
                {domain.verification_record_name}
              </code>
            </div>

            <div className="verification-record-row">
              <span>TYPE</span>

              <code>TXT</code>
            </div>

            <div className="verification-record-row">
              <span>VALUE</span>

              <code>
                {domain.verification_token}
              </code>
            </div>
          </div>

          <CopyCommand command={domain.verification_token || ''} label="Copy TXT record value" />

          {(verifyError || error) && (
            <div
              className="onboarding-error"
              role="alert"
            >
              <span>!</span>

              <p>
                {verifyError ||
                  error ||
                  "Verification failed."}
              </p>
            </div>
          )}

          <div className="onboarding-verification-actions">
            <button
              type="button"
              className="onboarding-secondary-button"
              onClick={() =>
                navigate("/onboarding/domain")
              }
              disabled={verifying || isLoading}
            >
              ← Change domain
            </button>

            <button
              type="button"
              className="onboarding-primary-button"
              onClick={() => void handleVerification(false)}
              disabled={verifying || isLoading}
            >
              {verifying ? (
                <>
                  <span className="onboarding-spinner" />
                  Verifying...
                </>
              ) : (
                <>
                  Verify DNS record
                  <span>→</span>
                </>
              )}
            </button>
          </div>

          {domain.local_verification_available && <div className="onboarding-security-note"><div>
            <strong>Local PhantomBank ownership challenge</strong>
            <p>From your PhantomBank directory, run the command below and paste this TXT value when prompted. This proves control of the local bank deployment; it is not public DNS ownership.</p>
            <CopyCommand command="python scripts/connect.py verify" label="Copy verification command" />
            <button type="button" className="demo-verification-button" disabled={verifying || isLoading} onClick={() => void handleVerification(true)}>Use local demo verification →</button>
          </div></div>}
          <button type="button" className="demo-verification-button" disabled={verifying} onClick={async () => {
            setVerifying(true); setVerifyError('');
            try { await apiPost(`/domains/${domain.id}/renew-challenge`); await refresh(); }
            catch (err) { setVerifyError(err instanceof Error ? err.message : 'Unable to renew challenge'); }
            finally { setVerifying(false); }
          }}>Renew expired challenge</button>
          <div className="onboarding-security-note">
            <span>◈</span>

            <div>
              <strong>
                DNS verification
              </strong>

              <p>
                In a production deployment, PhantomLayer
                checks the DNS record published by your
                organization. Demo verification is
                 available only for the reserved local bank domain while DEMO_MODE is enabled.
              </p>
            </div>
          </div>
        </section>

        <aside className="onboarding-info-panel">
          <span className="onboarding-eyebrow">
            VERIFICATION FLOW
          </span>

          <div className="onboarding-info-step">
            <span>01</span>

            <div>
              <strong>Copy the record</strong>

              <p>
                Create a TXT record using the name and
                value provided by PhantomLayer.
              </p>
            </div>
          </div>

          <div className="onboarding-info-line" />

          <div className="onboarding-info-step">
            <span>02</span>

            <div>
              <strong>Publish it in DNS</strong>

              <p>
                Add the record through your DNS provider
                and wait for propagation.
              </p>
            </div>
          </div>

          <div className="onboarding-info-line" />

          <div className="onboarding-info-step">
            <span>03</span>

            <div>
              <strong>Verify ownership</strong>

              <p>
                PhantomLayer validates the record before
                allowing protection configuration.
              </p>
            </div>
          </div>

          <div className="verification-domain-status">
            <span>STATUS</span>

            <div>
              <StatusPill status="pending" />
              <strong>
                Awaiting verification
              </strong>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
