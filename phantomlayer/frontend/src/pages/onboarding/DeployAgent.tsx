import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AgentStatusCard } from '../../components/AgentStatusCard';
import { LoadingScreen } from '../../components/LoadingScreen';
import { CopyCommand } from '../../components/CopyCommand';
import { useOrganization } from '../../hooks/useOrganization';
import { apiPost, registerAgent } from '../../lib/api';

export function DeployAgent() {
  const { verifiedDomain, protections, agents, refresh, isLoading, error } = useOrganization();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [credential, setCredential] = useState<{agent_id: string; registration_token: string} | null>(null);
  const [downloaded, setDownloaded] = useState(false);
  const agent = agents.find(a => a.domain_id === verifiedDomain?.id);
  const protection = protections.find(p => p.domain_id === verifiedDomain?.id && p.enabled);

  async function registerOrRotate() {
    if (!verifiedDomain || !protection) return;
    setBusy(true); setFailure(''); setDownloaded(false);
    try {
      const result = agent
        ? await apiPost<{agent_id: string; registration_token: string}>(`/agents/${agent.agent_id}/rotate-token`)
        : await registerAgent({name: 'PhantomBank API adapter', domain_id: verifiedDomain.id,
            version: '0.3.0', capabilities: ['api-protection', 'honeypot-routing', 'telemetry']});
      setCredential(result);
      await refresh();
    } catch (err) { setFailure(err instanceof Error ? err.message : 'Registration failed'); }
    finally { setBusy(false); }
  }

  function download() {
    if (!credential || !verifiedDomain || !protection) return;
    const blob = new Blob([JSON.stringify({format: 'phantomlayer-bank-v1',
      agent_id: credential.agent_id, agent_token: credential.registration_token,
      organization_id: protection.organization_id, domain_id: verifiedDomain.id, domain: verifiedDomain.domain}, null, 2)],
      {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = 'phantomlayer-integration.json'; link.click();
    URL.revokeObjectURL(url); setDownloaded(true);
  }

  if (isLoading) return <LoadingScreen message="Loading agent deployment…" />;
  return <div className="onboarding-page">
    <div className="onboarding-page-header"><span className="onboarding-eyebrow">STEP 05 / AGENT</span>
      <h1>Connect your<br /><span>customer infrastructure.</span></h1>
      <p>PhantomBank runs the adapter inside bank-api. Your account registers the agent; your bank installs its own credential.</p>
    </div>
    {!verifiedDomain || !protection ? <section className="onboarding-card"><h2>Complete domain and protection setup</h2>
      <Link to={verifiedDomain ? '/onboarding/protection' : '/onboarding/domain'}>Continue setup →</Link></section> : <>
      <div className="agent-deployment-layout"><section className="onboarding-card">
        <h2>1. Register the customer agent</h2>
        <p>Domain: <strong>{verifiedDomain.domain}</strong></p>
        <p>Organization: <code>{protection.organization_id}</code></p>
        <AgentStatusCard agent={agent ?? null} loading={busy} onRefresh={refresh} />
        {agent && !credential && <p>The previous credential cannot be retrieved. Rotate only if you need a replacement; the old credential stops working immediately.</p>}
        {!credential && <button className="onboarding-primary-button" disabled={busy} onClick={() => void registerOrRotate()}>
          {busy ? 'Preparing…' : agent ? 'Rotate credential and reconnect' : 'Register agent'}</button>}
        {credential && <div className="agent-registration-result">
          <h3>One-time customer configuration</h3>
          <p>The secret is held in memory only and is not displayed. Download it once, protect the file, and keep it out of source control. Reloading requires rotation.</p>
          <button className="onboarding-primary-button" onClick={download}>Download integration configuration</button>
          {downloaded && <p role="status">Configuration downloaded. Install it on your bank host below.</p>}
        </div>}
        {(failure || error) && <div className="onboarding-error" role="alert">{failure || error}</div>}
      </section><aside className="onboarding-info-panel">
        <h2>2. Install inside PhantomBank</h2>
        <p>Run from the PhantomBank directory. Replace the path if your download is elsewhere.</p>
        <CopyCommand command={'python scripts/connect.py install "$HOME/Downloads/phantomlayer-integration.json"'} label="Copy install command" />
        <p>The installer validates the credential’s organization and domain through the authenticated integration API, writes owner-only .env, and recreates bank-api. No database rows are changed.</p>
        <h2>3. Wait for connectivity</h2>
        <p>Every 30 seconds the embedded agent probes both local databases and reports health. Activation requires a fresh healthy agent, both databases, the installed adapter, verified ownership and enabled API protection.</p>
        <p>Real database credentials and records remain inside PhantomBank. Only operation metadata and deception counts leave the bank.</p>
        {protection.layer !== 'api' && <p>This bank demonstrates the API data path. Other selected layers need their own adapters; full protection here covers only the implemented API path.</p>}
      </aside></div>
      <div className="protection-selection-actions"><Link to="/onboarding/protection">← Protection</Link>
        {agent && <Link className="onboarding-primary-button" to="/onboarding/activation">Check activation →</Link>}</div>
    </>}
  </div>;
}
