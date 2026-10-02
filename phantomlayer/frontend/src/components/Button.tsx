import type {
  ButtonHTMLAttributes,
  ReactNode,
} from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "success";

export type ButtonSize =
  | "small"
  | "medium"
  | "large";

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  icon?: ReactNode;
}

export function Button({
  children,
  variant = "primary",
  size = "medium",
  loading = false,
  fullWidth = false,
  icon,
  disabled,
  className = "",
  ...props
}: ButtonProps) {
  const classes = [
    "pl-button",
    `pl-button-${variant}`,
    `pl-button-${size}`,
    fullWidth ? "pl-button-full" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      {...props}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {loading ? (
        <span
          className="pl-button-spinner"
          aria-hidden="true"
        />
      ) : icon ? (
        <span
          className="pl-button-icon"
          aria-hidden="true"
        >
          {icon}
        </span>
      ) : null}

      <span>{children}</span>
    </button>
  );
}