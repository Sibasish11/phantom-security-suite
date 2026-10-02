import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Icon, type IconName } from '../../components/Icon';
const steps: {icon:IconName; title:string; text:string}[] = [
  {icon:'globe',title:'Verify your domain',text:'Prove ownership with a DNS record. No traffic changes yet.'},
  {icon:'shield',title:'Configure protection',text:'Choose the security layer for your verified environment.'},
  {icon:'server',title:'Connect your agent',text:'Deploy locally and confirm connectivity before going live.'},
];
export function OnboardingWelcome() {
  const {session} = useAuth();
  const firstName = session?.user.full_name?.split(' ')[0] || 'there';
  return <div className="setup-welcome"><span className="section-tag"><Icon name="check" /> WORKSPACE CREATED</span><h1>Build your<br /><span>security layer.</span></h1><p className="setup-lead">Welcome, {firstName}. Your workspace is ready. Next, connect the environment you want to protect.</p><div className="setup-checklist">{steps.map((step,index) => <div key={step.title}><span className="setup-feature-icon"><Icon name={step.icon} /></span><div><span className="eyebrow">{String(index+1).padStart(2,'0')}</span><h3>{step.title}</h3><p>{step.text}</p></div></div>)}</div><div className="setup-welcome-actions"><Link to="/onboarding/domain" className="ui-primary">Begin deployment <Icon name="arrow" /></Link><Link to="/dashboard" className="text-link">Explore the workspace first ↗</Link></div><div className="ui-note"><Icon name="lock" /><p>Setup does not copy your production database or automatically enable protection. You control each step.</p></div></div>;
}
