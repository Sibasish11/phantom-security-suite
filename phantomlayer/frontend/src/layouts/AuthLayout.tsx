import type { ReactNode } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icon';

export function AuthLayout({ children }: { children?: ReactNode }) {
  return <div className="access-layout">
    <a className="skip-link" href="#access-main">Skip to content</a>
    <header className="access-header"><Link to="/" aria-label="PhantomLayer home"><Logo size="small" /></Link><Link className="text-link" to="/">← Back to home</Link></header>
    <main id="access-main" className="access-main">{children ?? <Outlet />}</main>
    <footer className="access-footer"><span>© {new Date().getFullYear()} PhantomLayer</span><span><Icon name="lock" /> Your infrastructure. Your data. Your control.</span></footer>
  </div>;
}
