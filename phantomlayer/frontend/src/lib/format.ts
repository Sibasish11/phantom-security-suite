export function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

export function formatDate(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatFullDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatRelativeTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  const difference =
    Date.now() - date.getTime();

  const seconds = Math.floor(
    difference / 1000,
  );

  if (seconds < 0) {
    return "just now";
  }

  if (seconds < 10) {
    return "just now";
  }

  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);

  if (days < 30) {
    return `${days}d ago`;
  }

  const months = Math.floor(days / 30);

  if (months < 12) {
    return `${months}mo ago`;
  }

  const years = Math.floor(days / 365);

  return `${years}y ago`;
}

export function formatNumber(
  value: number | null | undefined,
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN").format(
    value,
  );
}

export function formatPercentage(
  value: number | null | undefined,
  decimals = 0,
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "—";
  }

  return `${value.toFixed(decimals)}%`;
}

export function formatRiskScore(
  score: number | null | undefined,
): string {
  if (
    score === null ||
    score === undefined ||
    Number.isNaN(score)
  ) {
    return "—";
  }

  return Math.round(score).toString();
}

export function getRiskLevel(
  score: number | null | undefined,
): "low" | "medium" | "high" | "critical" {
  const normalized = Number(score ?? 0);

  if (normalized >= 80) {
    return "critical";
  }

  if (normalized >= 60) {
    return "high";
  }

  if (normalized >= 40) {
    return "medium";
  }

  return "low";
}

export function formatBytes(
  bytes: number | null | undefined,
): string {
  if (
    bytes === null ||
    bytes === undefined ||
    Number.isNaN(bytes)
  ) {
    return "—";
  }

  if (bytes === 0) {
    return "0 B";
  }

  const units = [
    "B",
    "KB",
    "MB",
    "GB",
    "TB",
  ];

  const exponent = Math.floor(
    Math.log(bytes) / Math.log(1024),
  );

  const unitIndex = Math.min(
    exponent,
    units.length - 1,
  );

  const value =
    bytes / Math.pow(1024, unitIndex);

  return `${value.toFixed(
    unitIndex === 0 ? 0 : 1,
  )} ${units[unitIndex]}`;
}

export function formatDuration(
  seconds: number | null | undefined,
): string {
  if (
    seconds === null ||
    seconds === undefined ||
    Number.isNaN(seconds)
  ) {
    return "—";
  }

  const totalSeconds = Math.max(
    0,
    Math.floor(seconds),
  );

  const days = Math.floor(
    totalSeconds / 86400,
  );

  const hours = Math.floor(
    (totalSeconds % 86400) / 3600,
  );

  const minutes = Math.floor(
    (totalSeconds % 3600) / 60,
  );

  const remainingSeconds =
    totalSeconds % 60;

  if (days > 0) {
    return `${days}d ${hours}h`;
  }

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

export function formatCount(
  value: number | null | undefined,
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "0";
  }

  if (value < 1000) {
    return value.toString();
  }

  if (value < 1_000_000) {
    return `${(value / 1000).toFixed(
      value >= 10_000 ? 0 : 1,
    )}K`;
  }

  if (value < 1_000_000_000) {
    return `${(value / 1_000_000).toFixed(
      value >= 10_000_000 ? 0 : 1,
    )}M`;
  }

  return `${(value / 1_000_000_000).toFixed(1)}B`;
}

export function truncate(
  value: string | null | undefined,
  maxLength: number,
): string {
  if (!value) {
    return "";
  }

  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, Math.max(0, maxLength - 1))}…`;
}

export function maskValue(
  value: string | null | undefined,
  visibleCharacters = 4,
): string {
  if (!value) {
    return "—";
  }

  if (value.length <= visibleCharacters) {
    return "••••";
  }

  return `${"•".repeat(
    Math.max(4, value.length - visibleCharacters),
  )}${value.slice(-visibleCharacters)}`;
}

export function formatIpAddress(
  value: string | null | undefined,
): string {
  return value || "Unknown source";
}

export function formatBoolean(
  value: boolean | null | undefined,
): string {
  if (value === true) {
    return "Yes";
  }

  if (value === false) {
    return "No";
  }

  return "—";
}