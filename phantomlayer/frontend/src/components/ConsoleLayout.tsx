import { type ReactNode, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Logo } from './Logo';
import { Icon, type IconName } from './Icon';
import { StatusPill } from './StatusPill';
import { useAuth } from '../hooks/useAuth';
import { useOrganization } from '../hooks/useOrganization';
import { getStoredOrganization } from '../lib/storage';
import { containDialogFocus } from '../lib/dialogFocus';

type NavItem = { label: string; path: string; icon: IconName };
const security: NavItem[] = [
  {label:'Overview',path:'/dashboard',icon:'grid'},
  {label:'Incidents',path:'/dashboard/incidents',icon:'alert'},
  {label:'Security events',path:'/dashboard/events',icon:'activity'},
  {label:'Sessions',path:'/dashboard/sessions',icon:'clock'},
  {label:'Protection',path:'/dashboard/protection',icon:'shield'},
  {label:'Agent',path:'/dashboard/agent',icon:'server'},
];
const administration: NavItem[] = [
  {label:'Overview',path:'/admin',icon:'grid'},
  {label:'Organizations',path:'/admin/organizations',icon:'building'},
  {label:'Domains',path:'/admin/domains',icon:'globe'},
  {label:'Agents',path:'/admin/agents',icon:'server'},
  {label:'Protections',path:'/admin/protections',icon:'shield'},
  {label:'Events',path:'/admin/events',icon:'activity'},
  {label:'Incidents',path:'/admin/incidents',icon:'alert'},
];
export function ConsoleLayout({ children, admin = false }: {children?: ReactNode; admin?: boolean}) {
  const {session, logout} = useAuth();
  const {verifiedDomain, connectedAgent, activeProtection} = useOrganization();
  const navigate = useNavigate();
  const {pathname} = useLocation();
  const dialog = useRef<HTMLDialogElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const organization = getStoredOrganization() as unknown as Record<string, unknown> | null;
  const orgName = typeof organization?.organization_name === 'string' ? organization.organization_name : typeof organization?.name === 'string' ? organization.name : 'Your organization';
  const userName = session?.user.full_name || session?.user.email || 'Security team';
  const items = admin ? administration : security;
  const current = [...administration, ...security].find(item => item.path === pathname)?.label || (pathname.includes('/incidents/') ? 'Investigation' : 'Settings');
  useEffect(() => { dialog.current?.close(); setMenuOpen(false); }, [pathname]);
  async function signOut() { await logout(); navigate('/login'); }
  const sidebar = <>
    <Link className="console-brand" to={admin ? '/admin' : '/dashboard'} aria-label="PhantomLayer dashboard"><Logo size="small" /></Link>
    <div className="console-workspace"><span className="workspace-avatar">{orgName[0].toUpperCase()}</span><div><small>ORGANIZATION WORKSPACE</small><strong title={orgName}>{orgName}</strong></div><Icon name="lock" /></div>
    <nav aria-label={admin ? 'Organization administration' : 'Security console'} className="console-nav" onClick={event => {if ((event.target as Element).closest('a')) {dialog.current?.close();setMenuOpen(false);}}}><span className="nav-caption">{admin ? 'ADMINISTRATION' : 'SECURITY OPERATIONS'}</span>{items.map(item => <NavLink key={item.path} to={item.path} end={item.path === '/admin' || item.path === '/dashboard'} className={({isActive}) => isActive ? 'console-nav-link active' : 'console-nav-link'}><Icon name={item.icon} /><span>{item.label}</span></NavLink>)}
      <span className="nav-caption">WORKSPACE</span>
      {!admin && session?.user.role === 'admin' && <NavLink className="console-nav-link" to="/admin/domains"><Icon name="globe" /><span>Domains</span></NavLink>}
      <NavLink className={({isActive}) => `console-nav-link${isActive ? ' active' : ''}`} to="/dashboard/settings"><Icon name="settings" /><span>Settings</span></NavLink>
      {session?.user.role === 'admin' && <Link className="console-nav-link" to={admin ? '/dashboard' : '/admin'}><Icon name={admin ? 'activity' : 'building'} /><span>{admin ? 'Security console' : 'Administration'}</span><span className="nav-external">↗</span></Link>}
    </nav>
    <div className="console-sidebar-bottom"><div className="console-posture"><span className="nav-caption">ENVIRONMENT</span><div><StatusPill status={connectedAgent?.status || 'pending'} size="small" /><span>Agent health</span></div><small title={verifiedDomain?.domain}>{verifiedDomain?.domain || 'Domain verification pending'}</small></div><div className="console-user"><span className="user-avatar">{userName[0].toUpperCase()}</span><div><strong title={userName}>{userName}</strong><small>{admin ? 'Organization administrator' : 'Security workspace'}</small></div><button className="icon-button" onClick={signOut} aria-label="Log out" title="Log out"><Icon name="logOut" /></button></div></div>
  </>;
  return <div className="console-layout"><a className="skip-link" href="#console-main">Skip to content</a><aside className="console-sidebar">{sidebar}</aside>
    <dialog ref={dialog} className="console-mobile-drawer" aria-label="Workspace navigation" onKeyDown={containDialogFocus} onClose={() => setMenuOpen(false)} onClick={e => {if (e.target === e.currentTarget) dialog.current?.close();}}><button className="drawer-close icon-button" onClick={() => dialog.current?.close()} aria-label="Close navigation"><Icon name="close" /></button>{sidebar}</dialog>
    <div className="console-main"><header className="console-topbar"><div className="console-crumb"><button className="console-menu icon-button" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => {dialog.current?.showModal();setMenuOpen(true);}}><Icon name="menu" /></button><span>{admin ? 'Administration' : 'Security console'}</span><b>/</b><strong>{current}</strong></div><div className="console-topbar-right"><span className="console-scope"><Icon name="lock" /> Tenant-scoped</span>{activeProtection && <StatusPill status="active" size="small" />}</div></header><main id="console-main" className={`${admin ? 'admin-content' : 'customer-content'} console-content`}>{children ?? <Outlet />}</main><footer className="console-footer"><span>PhantomLayer <span className="muted">/ Cyber deception</span></span><Link to="/how-it-works">Understand the protection path ↗</Link></footer></div>
  </div>;
}
