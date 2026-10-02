import { Icon } from './Icon';

/** An explanatory diagram, deliberately not presented as live telemetry. */
export function RoutingPreview() {
  return <div className="routing-preview" aria-label="Illustration: requests assessed by PhantomLayer reach either real or isolated synthetic data">
    <div className="preview-heading"><span className="eyebrow">A DIFFERENT DESTINATION</span><span>Architecture preview</span></div>
    <div className="preview-request"><Icon name="globe" /><div><strong>Your application</strong><small>One familiar experience</small></div><code>REQUEST</code></div>
    <div className="preview-connector" aria-hidden="true" />
    <div className="preview-engine"><div className="preview-engine-icon"><Icon name="shield" /></div><div><strong>PhantomLayer</strong><small>Detect · assess · route</small></div><span className="preview-rule">Rule-based</span></div>
    <div className="preview-fork" aria-hidden="true"><span /><span /></div>
    <div className="preview-destinations"><div><Icon name="server" /><strong>Real environment</strong><span>Legitimate operations</span><small>Customer-controlled data</small></div><div><Icon name="layers" /><strong>Deception</strong><span>Suspicious operations</span><small>Isolated synthetic data</small></div></div>
    <div className="preview-evidence"><Icon name="activity" /><span>Every observed interaction becomes evidence.</span></div>
  </div>;
}
