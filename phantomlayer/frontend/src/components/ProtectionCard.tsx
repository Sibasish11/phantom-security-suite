import type { Protection } from "../types/protection";
import { StatusPill } from "./StatusPill";

interface ProtectionCardProps {
  protection: Protection | null;
  domainName?: string;
  loading?: boolean;
  onConfigure?: () => void;
  onManage?: () => void;
}

const LAYER_LABELS: Record<string, string> = {
  api: "API Protection",
  database: "Database Protection",
  internal: "Internal Protection",
  full: "Full Protection",
};

const LAYER_DESCRIPTIONS: Record<string, string> = {
  api: "Protect application and API traffic with intelligent deception routing.",
  database: "Protect database access and redirect suspicious queries into an isolated honeypot.",
  internal: "Protect internal infrastructure and detect suspicious activity across trusted networks.",
  full: "Combine API, database and internal deception layers into one protection surface.",
};

function getLayerLabel(layer: string): string {
  return (
    LAYER_LABELS[layer] ??
    layer
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, (character) =>
        character.toUpperCase(),
      )
  );
}

function getLayerDescription(layer: string): string {
  return (
    LAYER_DESCRIPTIONS[layer] ??
    "Security protection configured through PhantomLayer."
  );
}

export function ProtectionCard({
  protection,
  domainName,
  loading = false,
  onConfigure,
  onManage,
}: ProtectionCardProps) {
  if (loading) {
    return (
      <section className="protection-card protection-card-loading">
        <div className="protection-skeleton-icon" />

        <div className="protection-skeleton-title" />

        <div className="protection-skeleton-line" />

        <div className="protection-skeleton-line protection-skeleton-short" />
      </section>
    );
  }

  if (!protection) {
    return (
      <section className="protection-card protection-card-empty">
        <div className="protection-card-icon protection-card-icon-idle">
          ◈
        </div>

        <div className="protection-card-content">
          <span className="protection-card-kicker">
            PROTECTION LAYER
          </span>

          <h3>No protection configured</h3>

          <p>
            Choose a protection layer for your verified
            domain. PhantomLayer will configure the
            deception environment before activation.
          </p>

          {onConfigure && (
            <button
              type="button"
              className="protection-action-button"
              onClick={onConfigure}
            >
              Configure protection
              <span>→</span>
            </button>
          )}
        </div>
      </section>
    );
  }

  const layer = protection.layer;

  return (
    <section className="protection-card">
      <div className="protection-card-top">
        <div className="protection-card-icon">
          ◈
        </div>

        <StatusPill
          status={protection.status}
          size="small"
        />
      </div>

      <div className="protection-card-content">
        <span className="protection-card-kicker">
          PROTECTION LAYER
        </span>

        <h3>{getLayerLabel(layer)}</h3>

        <p>
          {getLayerDescription(layer)}
        </p>

        {domainName && (
          <div className="protection-domain">
            <span className="protection-domain-icon">
              ◉
            </span>

            <span>{domainName}</span>
          </div>
        )}
      </div>

      <div className="protection-card-footer">
        <div className="protection-state">
          <span
            className={[
              "protection-state-dot",
              protection.enabled &&
              protection.status === "active"
                ? "protection-state-active"
                : "protection-state-inactive",
            ].join(" ")}
          />

          <span>
            {protection.enabled &&
            protection.status === "active"
              ? "Protection active"
              : "Protection not active"}
          </span>
        </div>

        {onManage && (
          <button
            type="button"
            className="protection-manage-button"
            onClick={onManage}
          >
            Manage
          </button>
        )}
      </div>
    </section>
  );
}