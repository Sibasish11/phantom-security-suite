interface LogoProps {
  compact?: boolean;
  showText?: boolean;
  size?: "small" | "medium" | "large";
}

export function Logo({
  compact = false,
  showText = true,
  size = "medium",
}: LogoProps) {
  const sizeClass =
    size === "small"
      ? "logo-size-small"
      : size === "large"
        ? "logo-size-large"
        : "logo-size-medium";

  return (
    <div
      className={`phantom-logo ${sizeClass} ${
        compact ? "phantom-logo-compact" : ""
      }`}
    >
      <div className="phantom-logo-mark">
        <span className="phantom-logo-core">P</span>

        <span className="phantom-logo-ring ring-one" />
        <span className="phantom-logo-ring ring-two" />
      </div>

      {showText && (
        <div className="phantom-logo-wordmark">
          <span className="phantom-logo-name">
            PhantomLayer
          </span>

          {!compact && (
            <span className="phantom-logo-tagline">
              CYBER DECEPTION
            </span>
          )}
        </div>
      )}
    </div>
  );
}