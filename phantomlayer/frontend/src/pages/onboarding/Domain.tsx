import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatusPill } from "../../components/StatusPill";
import { LoadingScreen } from '../../components/LoadingScreen';
import { useOrganization } from "../../hooks/useOrganization";

export function DomainSetup() {
  const navigate = useNavigate();

  const {
    verifiedDomain,
    domains,
    addDomain,
    isLoading,
    error,
  } = useOrganization();

  const [domain, setDomain] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setFormError("");

    const normalizedDomain = domain
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/\/.*$/, "");

    if (!normalizedDomain) {
      setFormError("Enter a domain to continue.");
      return;
    }

    if (!normalizedDomain.includes(".")) {
      setFormError(
        "Enter a valid domain, such as example.com.",
      );
      return;
    }

    setSubmitting(true);
    try {
      const created = await addDomain(normalizedDomain);
      if (created) navigate("/onboarding/domain/verify");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Unable to connect this domain. Please try again.');
    } finally { setSubmitting(false); }
  }

  if (isLoading) return <LoadingScreen message="Loading your domains…" />;

  if (verifiedDomain) {
    return (
      <div className="onboarding-page">
        <section className="onboarding-card onboarding-card-success">
          <div className="onboarding-success-icon">
            ✓
          </div>

          <span className="onboarding-eyebrow">
            DOMAIN READY
          </span>

          <h1>
            Your domain is
            <br />
            <span>already verified.</span>
          </h1>

          <p>
            PhantomLayer can continue configuring
            protection for this domain.
          </p>

          <div className="onboarding-domain-preview">
            <div>
              <span>PROTECTED DOMAIN</span>
              <strong>{verifiedDomain.domain}</strong>
            </div>

            <StatusPill status="verified" />
          </div>

          <button
            type="button"
            className="onboarding-primary-button"
            onClick={() =>
              navigate("/onboarding/protection")
            }
          >
            Continue
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
          STEP 02 / DOMAIN
        </span>

        <h1>
          What should
          <br />
          <span>we protect?</span>
        </h1>

        <p>
          Start by connecting a domain owned by your
          organization. PhantomLayer uses domain
          verification to make sure you control it.
        </p>
      </div>

      <div className="onboarding-domain-layout">
        <section className="onboarding-card">
          <div className="onboarding-card-header">
            <div className="onboarding-card-icon">
              ◇
            </div>

            <div>
              <span>DOMAIN CONNECTION</span>
              <h2>Add your domain</h2>
            </div>
          </div>

          <form
            className="onboarding-form"
            onSubmit={handleSubmit}
          >
            <label className="onboarding-field">
              <span>Domain name</span>

              <input
                type="text"
                value={domain}
                onChange={(event) =>
                  setDomain(event.target.value)
                }
                placeholder="example.com"
                autoComplete="off"
                spellCheck={false}
                required
                aria-invalid={Boolean(formError)}
                disabled={isLoading || submitting}
              />

              <small>
                Don't include http://, https:// or a path.
              </small>
            </label>

            {(formError || error) && (
              <div
                className="onboarding-error"
                role="alert"
              >
                <span>!</span>
                <p>{formError || error}</p>
              </div>
            )}

            <button
              type="submit"
              className="onboarding-primary-button"
              disabled={isLoading || submitting}
            >
              {isLoading || submitting ? (
                <>
                  <span className="onboarding-spinner" />
                  Adding domain...
                </>
              ) : (
                <>
                  Continue to verification
                  <span>→</span>
                </>
              )}
            </button>
          </form>

          <div className="onboarding-security-note">
            <span>◈</span>

            <div>
              <strong>
                Why do we verify ownership?
              </strong>

              <p>
                Domain verification prevents PhantomLayer
                from being configured against infrastructure
                you don't control.
              </p>
            </div>
          </div>
        </section>

        <aside className="onboarding-info-panel">
          <span className="onboarding-eyebrow">
            WHAT HAPPENS NEXT
          </span>

          <div className="onboarding-info-step">
            <span>01</span>
            <div>
              <strong>DNS verification</strong>
              <p>
                PhantomLayer gives you a unique DNS
                record to publish.
              </p>
            </div>
          </div>

          <div className="onboarding-info-line" />

          <div className="onboarding-info-step">
            <span>02</span>
            <div>
              <strong>Ownership confirmed</strong>
              <p>
                Once the record is detected, the domain
                becomes available for protection.
              </p>
            </div>
          </div>

          <div className="onboarding-info-line" />

          <div className="onboarding-info-step">
            <span>03</span>
            <div>
              <strong>Choose your layer</strong>
              <p>
                Select API, database, internal or full
                protection.
              </p>
            </div>
          </div>

          <div className="onboarding-info-domain">
            <span>CONNECTED DOMAINS</span>

            <strong>{domains.length}</strong>

            <small>
              Domain{domains.length === 1 ? "" : "s"} in
              your organization
            </small>
          </div>
        </aside>
      </div>
    </div>
  );
}