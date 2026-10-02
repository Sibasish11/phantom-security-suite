import { type FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/Button';
import { Icon } from '../../components/Icon';
import { RoutingPreview } from '../../components/RoutingPreview';

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); clearError();
    const session = await login({ email: email.trim(), password }).catch(() => null);
    if (session) {
      const from = location.state?.from;
      navigate(typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/dashboard', { replace: true });
    }
  }
  return <div className="access-grid access-grid-login">
    <section className="access-story"><span className="section-tag"><Icon name="shield" /> THE SECURITY CONTROL PLANE</span><h1>See the intent.<br /><span>Contain the impact.</span></h1><p>Your domains, agents, and attack evidence. One clear view of the security layer you control.</p><RoutingPreview /></section>
    <section className="access-form-panel" aria-labelledby="login-heading"><span className="eyebrow">WELCOME BACK</span><h2 id="login-heading">Sign in to your workspace</h2><p className="muted">Pick up where your investigation left off.</p>
      <form className="access-form" onSubmit={handleSubmit} aria-busy={isLoading}>
        {error && <div className="ui-alert ui-alert-error" role="alert"><Icon name="alert" /><div><strong>Sign in failed</strong><p>{error}</p></div></div>}
        <label htmlFor="login-email">Email address<input id="login-email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="username" required disabled={isLoading} /></label>
        <div className="access-field"><label htmlFor="login-password">Password</label><div className="password-control"><input id="login-password" type={visible ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" required disabled={isLoading} /><button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} onClick={() => setVisible(!visible)}><Icon name={visible ? 'eyeOff' : 'eye'} /></button></div></div>
        <Button type="submit" loading={isLoading} fullWidth>{isLoading ? 'Authenticating…' : 'Sign in'} {!isLoading && <Icon name="arrow" />}</Button>
      </form><div className="access-switch">New to PhantomLayer? <Link to="/signup">Create your organization ↗</Link></div><p className="access-form-note"><Icon name="lock" /> Access is scoped to your organization.</p>
    </section>
  </div>;
}
