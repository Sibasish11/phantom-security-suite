import { type FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Icon } from '../../components/Icon';
import { RoutingPreview } from '../../components/RoutingPreview';
import { Button } from '../../components/Button';

export function Signup() {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, isLoading, error, clearError } = useAuth();
  const [fullName, setFullName] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [validationError, setValidationError] = useState('');
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); clearError(); setValidationError('');
    if (organizationName.trim().length < 2 || fullName.trim().length < 2) {
      setValidationError('Enter your name and organization using at least two non-space characters.');
      return;
    }
    const session = await register({ full_name: fullName.trim(), organization_name: organizationName.trim(), email: email.trim(), password }).catch(() => null);
    if (session) {
      const from = location.state?.from;
      navigate(typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/onboarding', { replace: true });
    }
  }
  return <div className="access-grid">
    <section className="access-story"><span className="section-tag"><Icon name="shield" /> CYBER DECEPTION, BY DESIGN</span><h1>Build your<br /><span>security layer.</span></h1><p>Give suspicious traffic somewhere else to go. Create your workspace, connect your environment, and turn attacker activity into evidence.</p><RoutingPreview /><div className="access-assurance"><Icon name="lock" /><span>No production database upload.<br /><strong>Your infrastructure stays yours.</strong></span></div></section>
    <section className="access-form-panel" aria-labelledby="signup-heading"><div className="access-form-top"><span className="eyebrow">START WITH YOUR WORKSPACE</span><span className="access-step">01 / SETUP</span></div><h2 id="signup-heading">Create your organization</h2><p className="muted">Your team's private security workspace.</p>
      <form className="access-form" onSubmit={handleSubmit} aria-busy={isLoading}>
        {(validationError || error) && <div className="ui-alert ui-alert-error" role="alert"><Icon name="alert" /><div><strong>We couldn't create your organization</strong><p>{validationError || error}</p></div></div>}
        <label htmlFor="organization">Organization name<input id="organization" value={organizationName} onChange={e => setOrganizationName(e.target.value)} placeholder="Acme Security" autoComplete="organization" minLength={2} maxLength={150} required disabled={isLoading} /></label>
        <label htmlFor="full-name">Your full name<input id="full-name" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Alex Morgan" autoComplete="name" minLength={2} maxLength={150} required disabled={isLoading} /></label>
        <label htmlFor="signup-email">Work email<input id="signup-email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" required disabled={isLoading} /></label>
        <div className="access-field"><label htmlFor="signup-password">Create password</label><div className="password-control"><input id="signup-password" type={visible ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 8 characters" autoComplete="new-password" aria-describedby="password-help" minLength={8} maxLength={128} required disabled={isLoading} /><button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} disabled={isLoading} onClick={() => setVisible(!visible)}><Icon name={visible ? 'eyeOff' : 'eye'} /></button></div><small id="password-help">Use a unique password with at least 8 characters.</small></div>
        <Button type="submit" loading={isLoading} fullWidth>{isLoading ? 'Creating organization…' : 'Create organization'} {!isLoading && <Icon name="arrow" />}</Button>
        <p className="access-form-note"><Icon name="lock" /> No infrastructure credentials needed at this step.</p>
      </form><div className="access-switch">Already have a workspace? <Link to="/login">Sign in <span aria-hidden="true">↗</span></Link></div>
    </section>
  </div>;
}
