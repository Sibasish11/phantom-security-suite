import type { ReactNode } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icon';
const steps = [
  {path:'/onboarding', label:'Your workspace', detail:'A clear starting point'},
  {path:'/onboarding/domain', label:'Connect a domain', detail:'Choose your environment'},
  {path:'/onboarding/domain/verify', label:'Verify ownership', detail:'Confirm with a DNS record'},
  {path:'/onboarding/protection', label:'Choose protection', detail:'Configure your security layer'},
  {path:'/onboarding/agent', label:'Deploy an agent', detail:'Connect from your infrastructure'},
  {path:'/onboarding/activation', label:'Check readiness', detail:'Review live deployment status'},
];
export function OnboardingLayout({children}: {children?: ReactNode}) {
  const {pathname} = useLocation();
  const current = Math.max(0, steps.findIndex(step => step.path === pathname));
  return <div className="setup-layout"><a className="skip-link" href="#setup-main">Skip to setup</a><header className="access-header"><Link to="/" aria-label="PhantomLayer home"><Logo size="small" /></Link><Link className="text-link" to="/dashboard">Go to workspace <span aria-hidden="true">↗</span></Link></header>
    <div className="setup-frame"><aside className="setup-sidebar"><span className="eyebrow">YOUR SECURITY LAYER</span><h2>A clear path<br />to protection.</h2><p>Connect your environment.<br />Keep control of your data.</p><nav aria-label="Setup progress"><ol>{steps.map((step,index) => <li key={step.path} className={index === current ? 'current' : index < current ? 'visited' : ''}><Link to={step.path} aria-current={index === current ? 'step' : undefined}><span className="setup-number">{String(index+1).padStart(2,'0')}</span><div><strong>{step.label}</strong><small>{step.detail}</small></div></Link></li>)}</ol></nav><div className="setup-reassurance"><Icon name="lock" /><p>Only configuration and security telemetry reach the control plane. Your database credentials stay local.</p></div></aside><main id="setup-main" className="setup-content"><div className="setup-position"><span>ORGANIZATION SETUP</span><span>Step {current+1} of {steps.length}</span></div>{children ?? <Outlet />}</main></div><footer className="access-footer"><span>PhantomLayer / Secure deployment</span><Link to="/how-it-works">How the integration works ↗</Link></footer>
  </div>;
}
