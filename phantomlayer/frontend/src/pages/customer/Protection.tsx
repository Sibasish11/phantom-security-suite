import { useEffect, useState } from "react";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { StatusPill } from "../../components/StatusPill";

import { useOrganization } from "../../hooks/useOrganization";

import {
  updateProtection,
} from "../../lib/api";

import type {
  ProtectionLayer,
} from "../../types/protection";

function formatLayer(
  layer?: string,
): string {
  if (!layer) {
    return "Not configured";
  }

  return layer
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function getLayerDescription(
  layer: ProtectionLayer,
): string {
  switch (layer) {
    case "api":
      return "Protect application and API traffic with detection, risk scoring and intelligent deception routing.";

    case "database":
      return "Protect database access by detecting suspicious queries and routing hostile activity into an isolated honeypot.";

    case "internal":
      return "Detect suspicious internal activity and provide deception capabilities across protected infrastructure.";

    case "full":
      return "Combine API, database and internal deception into a broader PhantomLayer protection deployment.";

    default:
      return "PhantomLayer deception protection.";
  }
}

function getLayerIcon(
  layer: ProtectionLayer,
): string {
  switch (layer) {
    case "api":
      return "⌁";

    case "database":
      return "◇";

    case "internal":
      return "◎";

    case "full":
      return "◈";

    default:
      return "◈";
  }
}

export function Protection() {
  const {
    activeProtection: active,
    protections,
    error: loadError,
    verifiedDomain,
    connectedAgent,
    refresh,
    isLoading,
  } = useOrganization();

  const activeProtection = active ?? protections.find(p => p.domain_id === verifiedDomain?.id) ?? null;

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [enabled, setEnabled] =
    useState(
      activeProtection?.enabled ?? false,
    );

  useEffect(() => {
    setEnabled(
      activeProtection?.enabled ?? false,
    );
  }, [activeProtection?.enabled]);

  async function handleToggle() {
    if (!activeProtection) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setMessage(null);

      await updateProtection(
        activeProtection.id,
        {
          enabled: !enabled,
        },
      );

      setEnabled(!enabled);

      await refresh();

      setMessage(
        !enabled
          ? "Protection has been enabled."
          : "Protection has been paused.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update protection.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="customer-protection-page">
        <div className="customer-page-loading">
          <div className="customer-loading-orb">
            ◈
          </div>

          <strong>
            Loading protection...
          </strong>

          <span>
            Synchronizing your protection
            configuration.
          </span>
        </div>
      </div>
    );
  }

  if (loadError && !activeProtection) return <div className="ui-alert ui-alert-error" role="alert"><div><h1>Protection unavailable</h1><p>{loadError}</p><Button variant="secondary" onClick={() => void refresh()}>Retry</Button></div></div>;

  if (!activeProtection) {
    return (
      <div className="customer-protection-page">
        <section className="customer-page-header">
          <div>
            <span className="customer-eyebrow">
              PROTECTION CONTROL
            </span>

            <h1>
              Protection
            </h1>

            <p>
              Configure and manage your PhantomLayer
              security layer.
            </p>
          </div>
        </section>

        <div className="customer-protection-empty">
          <div className="customer-empty-icon">
            ◈
          </div>

          <h2>
            No protection configured
          </h2>

          <p>
            Choose a PhantomLayer protection layer
            during onboarding before managing it here.
          </p>

          <a
            href="/onboarding/protection"
            className="customer-primary-link"
          >
            Configure protection →
          </a>
        </div>
      </div>
    );
  }

  const layer =
    activeProtection.layer;

  const configuration =
    activeProtection.configuration ?? {};

  const riskThreshold =
    typeof configuration.risk_threshold ===
    "number"
      ? configuration.risk_threshold
      : null;

  return (
    <div className="customer-protection-page">
      {/* HEADER */}

      <section className="customer-page-header">
        <div>
          <span className="customer-eyebrow">
            PROTECTION CONTROL
          </span>

          <h1>
            Protection
          </h1>

          <p>
            Manage how PhantomLayer detects and
            responds to suspicious activity.
          </p>
        </div>

        <StatusPill
          status={
             loadError ? 'unavailable' : activeProtection.status
          }
        />
      </section>

      {/* MAIN PROTECTION CARD */}

      <section className="protection-control-card">
        <div className="protection-control-top">
          <div className="protection-control-icon">
            {getLayerIcon(layer)}
          </div>

          <div className="protection-control-title">
            <span>
              CONFIGURED PROTECTION LAYER
            </span>

            <h2>
              {formatLayer(layer)}
            </h2>

            <p>
              {getLayerDescription(layer)}
            </p>
          </div>

          <Badge
            variant={
              enabled
                ? "success"
                : "warning"
            }
          >
            {enabled
              ? "ENABLED"
              : "PAUSED"}
          </Badge>
        </div>

        <div className="protection-control-divider" />

        {/* DOMAIN */}

        <div className="protection-info-grid">
          <div className="protection-info-item">
            <span>
              PROTECTED DOMAIN
            </span>

            <strong>
              {verifiedDomain?.domain ??
                "Not configured"}
            </strong>

            <small>
              Verified customer domain
            </small>
          </div>

          <div className="protection-info-item">
            <span>
              CONFIGURED REFERENCE
            </span>

            <strong>
              {riskThreshold ?? 'Integration policy'}
            </strong>

            <small>
              Metadata only; routing uses integration rules
            </small>
          </div>

          <div className="protection-info-item">
            <span>
              AGENT
            </span>

            <strong>
              {connectedAgent?.name ??
                "Not connected"}
            </strong>

            <small>
              Infrastructure connector
            </small>
          </div>

          <div className="protection-info-item">
            <span>
              MODE
            </span>

            <strong>
              {typeof configuration.mode ===
              "string"
                ? formatLayer(
                    configuration.mode,
                  )
                : "Deception"}
            </strong>

            <small>
              Traffic handling mode
            </small>
          </div>
        </div>

        {/* TOGGLE */}

        <div className="protection-toggle-row">
          <div>
            <strong>
              Protection status
            </strong>

            <span>
               {enabled
                 ? loadError ? 'Unable to refresh integration readiness.' : activeProtection.status === 'active' ? "PhantomLayer is actively protecting this deployment." : (activeProtection.readiness_blockers ?? ['Waiting for integration readiness']).join('. ')
                : "Protection is currently paused for this deployment."}
            </span>
          </div>

          <Button
            variant={
              enabled
                ? "danger"
                : "success"
            }
            size="medium"
            loading={saving}
            onClick={
              handleToggle
            }
          >
            {enabled
              ? "Pause protection"
              : "Enable protection"}
          </Button>
        </div>
      </section>

      {/* ARCHITECTURE */}

      <section className="protection-architecture">
        <div className="customer-section-heading">
          <div>
            <span className="customer-eyebrow">
              TRAFFIC ARCHITECTURE
            </span>

            <h2>
              How protection works
            </h2>
          </div>
        </div>

        <div className="protection-flow">
          <div className="protection-flow-node">
            <span>01</span>

            <div>
              <strong>
                Incoming traffic
              </strong>

              <small>
                Requests enter through your
                protected application.
              </small>
            </div>
          </div>

          <div className="protection-flow-arrow">
            →
          </div>

          <div className="protection-flow-node protection-flow-active">
            <span>02</span>

            <div>
              <strong>
                PhantomLayer
              </strong>

              <small>
                Detection and risk scoring evaluate
                the request.
              </small>
            </div>
          </div>

          <div className="protection-flow-arrow">
            →
          </div>

          <div className="protection-flow-split">
            <div className="protection-flow-destination real">
              <strong>
                REAL
              </strong>

              <small>
                Legitimate traffic
              </small>
            </div>

            <div className="protection-flow-destination honeypot">
              <strong>
                HONEYPOT
              </strong>

              <small>
                Suspicious traffic
              </small>
            </div>
          </div>
        </div>
      </section>

      {/* SECURITY RULES */}

      <section className="protection-rules">
        <div className="customer-section-heading">
          <div>
            <span className="customer-eyebrow">
              DECISION ENGINE
            </span>

            <h2>
              Protection behaviour
            </h2>
          </div>
        </div>

        <div className="protection-rules-grid">
          <div className="protection-rule">
            <div className="protection-rule-icon">
              01
            </div>

            <div>
              <strong>
                Detect
              </strong>

              <p>
                PhantomLayer analyzes requests for
                reconnaissance, enumeration and
                sensitive data access patterns.
              </p>
            </div>
          </div>

          <div className="protection-rule">
            <div className="protection-rule-icon">
              02
            </div>

            <div>
              <strong>
                Score
              </strong>

              <p>
                Multiple security signals contribute
                to a risk score for each request.
              </p>
            </div>
          </div>

          <div className="protection-rule">
            <div className="protection-rule-icon">
              03
            </div>

            <div>
              <strong>
                Deceive
              </strong>

              <p>
                Suspicious sessions can be redirected
                into an isolated honeypot environment.
              </p>
            </div>
          </div>
        </div>
      </section>

      {message && (
        <div className="customer-success-message" role="status">
          <span>✓</span>
          {message}
        </div>
      )}

      {(error || loadError) && (
        <div className="customer-error-message" role="alert">
          <span>!</span>
          <p>{error || loadError}</p>
        </div>
      )}
    </div>
  );
}
