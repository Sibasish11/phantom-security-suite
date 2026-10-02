import { useState } from "react";

interface CopyCommandProps {
  command: string;
  label?: string;
}

export function CopyCommand({
  command,
  label = "Deployment command",
}: CopyCommandProps) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  async function copyCommand() {
    try {
      setError('');
      await navigator.clipboard.writeText(command);

      setCopied(true);

      window.setTimeout(() => {
        setCopied(false);
      }, 1800);
    } catch {
      setCopied(false);
      setError('Clipboard unavailable. Select and copy the command below.');
    }
  }

  return (
    <div className="copy-command">
      <div className="copy-command-header">
        <span>{label}</span>

        <button
          type="button"
          onClick={copyCommand}
          className="copy-command-button"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>

      <span className="copy-feedback" role="status">{error || (copied ? 'Copied to clipboard.' : '')}</span>
      <div className="copy-command-body">
        <span className="copy-command-prompt">
          $
        </span>

        <code>{command}</code>
      </div>
    </div>
  );
}