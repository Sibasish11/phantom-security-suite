import { useEffect, useState } from "react";
import { LoadingScreen } from '../../components/LoadingScreen';
import { useNavigate } from "react-router-dom";
import { createProtection, updateProtection } from "../../lib/api";
import { useOrganization } from "../../hooks/useOrganization";
import type { ProtectionLayer } from "../../types/protection";

const protectionOptions: Array<{
  layer: ProtectionLayer;
  number: string;
  icon: string;
  name: string;
  description: string;
  protects: string;
}> = [
  {
    layer: "api",
    number: "01",
    icon: "⌁",
    name: "API Protection",
    description:
      "Detect suspicious API requests, reconnaissance and enumeration before they reach sensitive application resources.",
    protects: "Application and API traffic",
  },
  {
    layer: "database",
    number: "02",
    icon: "◆",
    name: "Database Deception",
    description:
      "Use an isolated honeypot database to observe suspicious database activity without exposing production data.",
    protects: "Database access and queries",
  },
  {
    layer: "internal",
    number: "03",
    icon: "⬡",
    name: "Internal Protection",
    description:
      "Extend deception into internal infrastructure and identify suspicious activity moving through trusted environments.",
    protects: "Internal infrastructure",
  },
  {
    layer: "full",
    number: "04",
    icon: "◈",
    name: "Full Protection",
    description:
      "Combine multiple protection layers into a unified deception architecture across your infrastructure.",
    protects: "Application, database and internal layers",
  },
];

export function ChooseProtection() {
  const navigate = useNavigate();

  const {
    verifiedDomain,
    activeProtection,
    protections,
    isLoading,
    error,
    refresh,
  } = useOrganization();

  const [selectedLayer, setSelectedLayer] =
    useState<ProtectionLayer>(
      activeProtection?.layer ?? "api",
    );

  const configuredProtection = protections.find(p => p.domain_id === verifiedDomain?.id && p.enabled);
  useEffect(() => { if (configuredProtection) setSelectedLayer(configuredProtection.layer); }, [configuredProtection?.id]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  async function handleContinue() {
    setSaveError("");

    if (configuredProtection?.layer === selectedLayer) {
      navigate("/onboarding/agent");
      return;
    }

    if (!verifiedDomain) {
      navigate("/onboarding/domain");
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
      setSaveError(
        "The verified domain ID could not be found.",
      );
      return;
    }

    setSaving(true);

    try {
      const existing = protections.find(p => p.domain_id === domainId);
      if (existing) await updateProtection(existing.id, {layer: selectedLayer, enabled: true});
      else await createProtection({
        domain_id: domainId,
        layer: selectedLayer,
        configuration: {
          mode: "deception",
          risk_threshold: 40,
        },
      });

      await refresh();

      navigate("/onboarding/agent");
    } catch (err) {
      setSaveError(
        err instanceof Error
          ? err.message
          : "Unable to configure protection.",
      );
    } finally {
      setSaving(false);
    }
  }

  const busy = isLoading || saving;
  if (isLoading) return <LoadingScreen message="Loading protection configuration…" />;

  if (!verifiedDomain) {
    return (
      <div className="onboarding-page">
        <section className="onboarding-card">
          <span className="onboarding-eyebrow">
            STEP 04 / PROTECTION
          </span>

          <h1>
            Verify your
            <br />
            <span>domain first.</span>
          </h1>

          <p>
            A verified domain is required before a
            protection layer can be configured.
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

  const domainData =
    verifiedDomain as unknown as Record<
      string,
      unknown
    >;

  const domainName =
    typeof domainData.domain === "string"
      ? domainData.domain
      : "Verified domain";

  return (
    <div className="onboarding-page">
      <div className="onboarding-page-header">
        <span className="onboarding-eyebrow">
          STEP 04 / PROTECTION
        </span>

        <h1>
          Choose your
          <br />
          <span>protection layer.</span>
        </h1>

        <p>
          Select where PhantomLayer should introduce its
          detection and deception capabilities.
        </p>

        <div className="onboarding-domain-chip">
          <span>DOMAIN</span>

          <strong>{domainName}</strong>

          <span className="onboarding-domain-check">
            ✓
          </span>
        </div>
      </div>

      <p className="ui-note">Choose a configuration, then connect the matching customer-side integration. The demonstrated PhantomBank adapter enforces API/full protection; other layer configurations do not install additional coverage automatically.</p>
      <div className="protection-selection-grid">
        {protectionOptions.map((option) => {
          const selected =
            selectedLayer === option.layer;

          return (
            <button
              key={option.layer}
              type="button"
              className={[
                "protection-selection-card",
                selected
                  ? "protection-selection-card-selected"
                  : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() =>
                setSelectedLayer(option.layer)
              }
              disabled={busy}
              aria-pressed={selected}
            >
              <div className="protection-selection-top">
                <span>{option.number}</span>

                <strong>{option.icon}</strong>

                <span
                  className={[
                    "protection-selection-radio",
                    selected
                      ? "protection-selection-radio-selected"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {selected ? "✓" : ""}
                </span>
              </div>

              <div className="protection-selection-content">
                <span>
                  {option.layer.toUpperCase()}
                </span>

                <h2>{option.name}</h2>

                <p>{option.description}</p>
              </div>

              <div className="protection-selection-footer">
                <span>PROTECTS</span>

                <strong>{option.protects}</strong>
              </div>
            </button>
          );
        })}
      </div>

      {(error || saveError) && (
        <div
          className="onboarding-error"
          role="alert"
        >
          <span>!</span>

          <p>{saveError || error}</p>
        </div>
      )}

      <div className="protection-selection-bottom">
        <div className="protection-selection-note">
          <span>◈</span>

          <div>
            <strong>
              You can change this later.
            </strong>

            <p>
              Protection configuration can be updated
              from your security dashboard after deployment.
            </p>
          </div>
        </div>

        <div className="protection-selection-actions">
          <button
            type="button"
            className="onboarding-secondary-button"
            onClick={() =>
              navigate("/onboarding/domain/verify")
            }
            disabled={busy}
          >
            ← Back
          </button>

          <button
            type="button"
            className="onboarding-primary-button"
            onClick={handleContinue}
            disabled={busy}
          >
            {busy ? (
              <>
                <span className="onboarding-spinner" />
                Configuring...
              </>
            ) : (
              <>
                Continue to agent
                <span>→</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
