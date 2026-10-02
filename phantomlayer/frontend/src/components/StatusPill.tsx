import { Badge, type BadgeVariant } from "./Badge";

type Status =
  | "healthy"
  | "pending"
  | "degraded"
  | "offline"
  | "active"
  | "configuring"
  | "paused"
  | "connected"
  | "disconnected"
  | "verified"
  | "unverified"
  | "open"
  | "investigating"
  | "resolved"
  | "closed"
  | "low"
  | "medium"
  | "high"
  | "critical"
  | string;

interface StatusPillProps {
  status: Status;
  size?: "small" | "medium";
  dot?: boolean;
}

interface StatusConfig {
  label: string;
  variant: BadgeVariant;
}

const STATUS_CONFIG: Record<
  string,
  StatusConfig
> = {
  real: { label: "Real", variant: "success" },
  honeypot: { label: "Deception", variant: "purple" },
  blocked: { label: "Blocked", variant: "danger" },
  enabled: { label: "Enabled", variant: "success" },
  disabled: { label: "Disabled", variant: "neutral" },
  error: { label: "Error", variant: "danger" },
  failed: { label: "Failed", variant: "danger" },
  completed: { label: "Analyzed", variant: "purple" },
  analyzing: { label: "Analyzing", variant: "info" },
  healthy: {
    label: "Healthy",
    variant: "success",
  },

  pending: {
    label: "Pending",
    variant: "warning",
  },

  degraded: {
    label: "Degraded",
    variant: "warning",
  },

  offline: {
    label: "Offline",
    variant: "danger",
  },

  active: {
    label: "Active",
    variant: "success",
  },

  configuring: {
    label: "Configuring",
    variant: "warning",
  },

  paused: {
    label: "Paused",
    variant: "neutral",
  },

  connected: {
    label: "Connected",
    variant: "success",
  },

  disconnected: {
    label: "Disconnected",
    variant: "danger",
  },

  verified: {
    label: "Verified",
    variant: "success",
  },

  unverified: {
    label: "Unverified",
    variant: "warning",
  },

  open: {
    label: "Open",
    variant: "danger",
  },

  investigating: {
    label: "Investigating",
    variant: "warning",
  },

  resolved: {
    label: "Resolved",
    variant: "success",
  },

  closed: {
    label: "Closed",
    variant: "neutral",
  },

  low: {
    label: "Low",
    variant: "success",
  },

  medium: {
    label: "Medium",
    variant: "info",
  },

  high: {
    label: "High",
    variant: "warning",
  },

  critical: {
    label: "Critical",
    variant: "danger",
  },
};

function formatUnknownStatus(
  status: string,
): string {
  return status
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

export function StatusPill({
  status,
  size = "medium",
  dot = true,
}: StatusPillProps) {
  const normalizedStatus =
    status.toLowerCase();

  const config =
    STATUS_CONFIG[normalizedStatus];

  const label =
    config?.label ??
    formatUnknownStatus(status);

  const variant =
    config?.variant ?? "neutral";

  return (
    <Badge
      variant={variant}
      size={size}
      dot={dot}
    >
      {label}
    </Badge>
  );
}