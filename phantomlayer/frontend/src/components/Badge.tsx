import type { ReactNode } from "react";

export type BadgeVariant =
  | "neutral"
  | "purple"
  | "success"
  | "warning"
  | "danger"
  | "info";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  dot?: boolean;
  size?: "small" | "medium";
}

export function Badge({
  children,
  variant = "neutral",
  dot = false,
  size = "medium",
}: BadgeProps) {
  return (
    <span
      className={[
        "pl-badge",
        `pl-badge-${variant}`,
        `pl-badge-${size}`,
      ].join(" ")}
    >
      {dot && (
        <span
          className="pl-badge-dot"
          aria-hidden="true"
        />
      )}

      {children}
    </span>
  );
}