import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'

type Page = 'overview' | 'activity' | 'accounts' | 'cards' | 'profile' | 'support'
type User = { full_name: string; email: string }
type Account = { id: string; account_type: string; account_number: string; balance_cents: number; available_cents: number; currency: string; status: string }
type Transaction = { id: string; direction: 'in' | 'out'; amount_cents: number; merchant: string; description: string; category: string; occurred_at: string; status: string }
type Beneficiary = { id: string; name: string; account_hint: string; bank_name: string }
type Card = { id: string; card_name: string; card_number_masked: string; card_type: string; status: string; expires_on: string; spending_limit_cents: number }
type Profile = { full_name: string; email: string; phone: string; address: string; created_at: string }
type BankData = { user: User; accounts: Account[]; transactions: Transaction[]; beneficiaries: Beneficiary[]; cards: Card[]; profile: Profile | null; balance: { total_balance_cents: number; total_available_cents: number } }

const money = (cents: number, compact = false) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', notation: compact ? 'compact' : 'standard', maximumFractionDigits: 2 }).format(cents / 100)
const dateLabel = (value: string) => new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value))
const initials = (name: string) => name.split(' ').map((part) => part[0]).slice(0, 2).join('')

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const csrf = document.cookie.split('; ').find((part) => part.startsWith('bank_csrf='))?.split('=').slice(1).join('=')
  if (csrf) headers.set('X-CSRF-Token', decodeURIComponent(csrf))
  const response = await fetch(path, { ...options, headers, credentials: 'include' })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail || 'Something went wrong. Please try again.')
  }
  return response.json() as Promise<T>
}

function Mark({ inverse = false }: { inverse?: boolean }) {
  return <div className={`mark ${inverse ? 'mark-inverse' : ''}`}><span>p</span></div>
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState('maya.bennett@northstar.test')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const result = await api<{ user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      onLogin(result.user)
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in.') }
    finally { setBusy(false) }
  }
  return <main className="auth-page">
    <section className="auth-art">
      <div className="art-top"><Mark inverse /><span className="brand inverse-text">phantombank</span><span className="demo-pill">Fictional demo</span></div>
      <div className="art-copy"><p className="eyebrow inverse-text">Quiet confidence, by design</p><h1>Make room for the things that matter.</h1><p className="art-subtitle">A considered banking experience for your everyday, your ambitions, and the in-between.</p></div>
      <div className="art-footer"><span>Private banking demo</span><a href="/owner">Bank owner · Connect PhantomLayer →</a></div>
    </section>
    <section className="auth-panel">
      <div className="auth-form-wrap"><div className="mobile-brand"><Mark /><span className="brand">phantombank</span></div><p className="eyebrow">Welcome back</p><h2>Sign in to your bank</h2><p className="muted">See your money clearly. Move it thoughtfully.</p>
        <form onSubmit={submit} className="stack-form">
          <label>Email address<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary-button" type="submit" disabled={busy}>{busy ? <><span className="spinner" />Checking your details…</> : <>Sign in <span>→</span></>}</button>
        </form>
        <p className="secure-note"><span className="shield">◇</span> This is a fictional demo. No real funds or accounts are connected.</p>
      </div>
    </section>
  </main>
}

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [booting, setBooting] = useState(true)
  useEffect(() => {
    // This readable cookie is only a restoration hint, never authentication.
    // Both cookies are issued/expired together; the API still validates the
    // signed HttpOnly session before returning any customer information.
    if (!document.cookie.split('; ').some(part => part.startsWith('bank_csrf='))) {
      setBooting(false)
      return
    }
    api<{ user: User }>('/api/auth/session').then((result) => setUser(result.user)).catch(() => undefined).finally(() => setBooting(false))
  }, [])
  if (window.location.pathname === '/owner') return <OwnerSetup />
  if (booting) return <div className="boot-screen"><Mark /><span>Loading your space…</span></div>
  if (!user) return <Login onLogin={setUser} />
  return <BankApp user={user} onLogout={() => setUser(null)} />
}

function OwnerSetup() {
  const [info, setInfo] = useState<{domain: string; mode: string; configured: boolean} | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api<{domain: string; mode: string; configured: boolean}>('/api/integration-info').then(setInfo).catch(() => setError('Bank API unavailable. Start the local stack and reload.')) }, [])
  return <main className="content" style={{maxWidth: 1000, margin: 'auto'}}>
    <p className="eyebrow">Fictional customer · Local synthetic demonstration</p>
    <h1>Connect your bank to PhantomLayer</h1><p><a href="/">← Open banking application</a></p>
    {error && <p role="alert">{error}</p>}
    <section className="page-card"><h2>Your customer infrastructure</h2>
      <p>Domain: <strong>{info?.domain ?? 'Loading…'}</strong></p>
      <p>Deployment: <strong>{info?.mode === 'standalone' ? 'BEFORE — standalone synthetic bank, no protection' : info?.configured ? 'Adapter configured — confirm live readiness in PhantomLayer' : 'Waiting for customer integration'}</strong></p>
      <p>Maya Bennett is the legitimate synthetic customer. John Carter belongs to the separate deception database. No real funds or customers are connected.</p>
    </section>
    <section className="page-card"><h2>1. Account → organization → ownership</h2>
      <p><a href="http://localhost:3000/signup" target="_blank" rel="noreferrer">Create your PhantomLayer owner account ↗</a>. Signup creates your organization. Add <strong>phantombank.example.test</strong>.</p>
      <p>On your bank host, run <code>python scripts/connect.py verify</code> and paste the TXT challenge from PhantomLayer. Then click local demo verification. Production ownership uses DNS TXT.</p>
      <h2>2. Protection → customer agent</h2><p>Choose API Protection. Register the agent and download your one-time integration configuration.</p>
      <p>From this bank directory run <code>python scripts/connect.py install "$HOME/Downloads/phantomlayer-integration.json"</code>.</p>
      <p>The installer checks your agent’s organization and domain, stores its credential locally and restarts bank-api. Your database credentials and records stay here.</p>
      <h2>3. Healthy → active → investigate</h2><p>Open PhantomLayer’s activation page. Wait for domain verified, healthy heartbeat, real DB connected, honeypot connected and active protection. Open the SOC dashboard for incidents, timelines and labeled mock analysis.</p>
    </section>
    <section className="page-card"><h2>Presenter: same bounded attack, before and after</h2>
      <p>Before installing the adapter, run <code>python scripts/compare_attack.py before</code>. After activation run <code>python scripts/compare_attack.py after</code>. The commands use the same read-only allowlisted HTTP operations with a synthetic login and local presenter credential.</p>
      <p>Compare Maya on the unprotected real path with John in deception, risk/rules and unchanged dataset fingerprints. Pausing a configured SaaS protection fails closed; it never enables the unprotected baseline.</p>
    </section>
  </main>
}

function BankApp({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [page, setPage] = useState<Page>('overview')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [data, setData] = useState<BankData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const loadData = useCallback(async () => {
    setError('')
    try {
      const [accounts, transactions, beneficiaries, cards, profile, balance] = await Promise.all([
        api<{ accounts: Account[] }>('/api/accounts'), api<{ transactions: Transaction[] }>('/api/transactions'), api<{ beneficiaries: Beneficiary[] }>('/api/beneficiaries'), api<{ cards: Card[] }>('/api/cards'), api<{ profile: Profile }>('/api/profile'), api<BankData['balance']>('/api/balance'),
      ])
      setData({ user, accounts: accounts.accounts, transactions: transactions.transactions, beneficiaries: beneficiaries.beneficiaries, cards: cards.cards, profile: profile.profile, balance })
    } catch (err) { setError(err instanceof Error ? err.message : 'We could not load your accounts.') }
    finally { setLoading(false) }
  }, [user])
  useEffect(() => { loadData() }, [loadData])
  const logout = async () => { try { await api('/api/auth/logout', { method: 'POST' }) } finally { onLogout() } }
  return <div className="app-shell">
    <aside className="sidebar"><div className="sidebar-brand"><Mark /><span className="brand">phantombank</span></div><div className="side-label">Your banking</div><nav>{([['overview', 'Overview', '⌂'], ['activity', 'Activity', '↗'], ['accounts', 'Accounts', '▣'], ['cards', 'Cards', '▤']] as [Page, string, string][]).map(([id, label, icon]) => <button key={id} className={page === id ? 'nav-item active' : 'nav-item'} onClick={() => setPage(id)}><span>{icon}</span>{label}{id === 'activity' && <i className="nav-dot" />}</button>)}</nav><div className="side-label side-label-later">Personal</div><nav>{([['profile', 'Profile', '○'], ['support', 'Support', '?']] as [Page, string, string][]).map(([id, label, icon]) => <button key={id} className={page === id ? 'nav-item active' : 'nav-item'} onClick={() => setPage(id)}><span>{icon}</span>{label}</button>)}</nav><div className="sidebar-bottom"><div className="privacy-card"><span className="privacy-icon">✦</span><strong>Your privacy matters</strong><p>Your information is protected by design.</p><button className="text-button" onClick={() => setPage('support')}>How protection works ↗</button></div><button className="logout-button" onClick={logout}><span>↪</span> Sign out</button></div></aside>
    <div className="main-area"><header className="topbar"><div className="mobile-header"><button className="mobile-menu" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen((open) => !open)}>☰</button><Mark /></div><div className="topbar-actions"><button className="icon-button" title="Help" onClick={() => setPage('support')}>?</button><div className="user-menu"><div className="avatar">{initials(user.full_name)}</div><div className="user-menu-copy"><strong>{user.full_name}</strong><span>Personal banking</span></div><span className="chevron">⌄</span></div></div></header>{mobileOpen && <MobileNav page={page} onNavigate={(next) => { setPage(next); setMobileOpen(false) }} />}<main className="content"><div className="content-heading"><div><p className="eyebrow">{page === 'overview' ? new Date().toLocaleDateString('en-GB', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}) : 'Your banking'}</p><h1>{page === 'overview' ? `Welcome back, ${(data?.profile?.full_name || user.full_name).split(' ')[0]}` : pageTitle(page)}</h1></div>{page === 'overview' && <button className="outline-button" onClick={() => setPage('support')}>Need a hand? <span>↗</span></button>}</div>{error && <div className="error-banner" role="alert"><span>!</span><div><strong>We hit a snag</strong><p>{error}</p></div><button onClick={loadData}>Try again</button></div>}{loading ? <LoadingState /> : data ? <PageContent page={page} data={data} reload={loadData} openActivity={() => setPage('activity')} /> : <EmptyState title="Your banking space is unavailable" text="Try refreshing to reconnect." action={loadData} />}</main><footer className="app-footer"><span>PhantomBank is a fictional demo — no real funds.</span><span>Protected by design <b>✦</b></span></footer></div>
  </div>
}

function MobileNav({ page, onNavigate }: { page: Page; onNavigate: (page: Page) => void }) {
  const items: [Page, string][] = [['overview', 'Overview'], ['activity', 'Activity'], ['accounts', 'Accounts'], ['cards', 'Cards'], ['profile', 'Profile'], ['support', 'Support']]
  return <div className="mobile-nav">{items.map(([id, label]) => <button key={id} className={page === id ? 'active' : ''} onClick={() => onNavigate(id)}>{label}<span>→</span></button>)}</div>
}

function pageTitle(page: Page) { return ({ overview: 'Overview', activity: 'Activity', accounts: 'Accounts', cards: 'Your cards', profile: 'Profile', support: 'How can we help?' } satisfies Record<Page, string>)[page] }
function LoadingState() { return <div className="loading-grid"><div className="skeleton hero-skeleton" /><div className="skeleton" /><div className="skeleton wide-skeleton" /><div className="skeleton" /></div> }
function EmptyState({ title, text, action }: { title: string; text: string; action?: () => void }) { return <div className="empty-state"><div className="empty-icon">○</div><h3>{title}</h3><p>{text}</p>{action && <button className="outline-button" onClick={action}>Try again</button>}</div> }

function PageContent({ page, data, reload, openActivity }: { page: Page; data: BankData; reload: () => Promise<void>; openActivity: () => void }) {
  if (page === 'activity') return <ActivityPage data={data} />
  if (page === 'accounts') return <AccountsPage data={data} />
  if (page === 'cards') return <CardsPage cards={data.cards} />
  if (page === 'profile') return <ProfilePage profile={data.profile} />
  if (page === 'support') return <SupportPage />
  return <Overview data={data} reload={reload} openActivity={openActivity} />
}

function Overview({ data, reload, openActivity }: { data: BankData; reload: () => Promise<void>; openActivity: () => void }) {
  const [selected, setSelected] = useState(data.beneficiaries[0]?.id || '')
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const attempt = useRef({ payload: '', key: '' })
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ type: 'ok' | 'error'; text: string } | null>(null)
  const submit = async (event: FormEvent) => { event.preventDefault(); setMessage(null); setBusy(true); try { const payload = JSON.stringify({ source_account_id: data.accounts[0]?.id, beneficiary_id: selected, amount, reference: reference || 'Personal transfer' }); if (attempt.current.payload !== payload) attempt.current = { payload, key: crypto.randomUUID() }; await api('/api/transfers', { method: 'POST', headers: { 'X-Idempotency-Key': attempt.current.key }, body: payload }); attempt.current = { payload: '', key: '' };  setAmount(''); setReference(''); setMessage({ type: 'ok', text: 'Synthetic transfer completed. Your balance and activity are updated.' }); await reload() } catch (err) { setMessage({ type: 'error', text: err instanceof Error ? err.message : 'The transfer could not be completed.' }) } finally { setBusy(false) } }
  return <div className="overview-grid"><section className="balance-card"><div className="balance-card-top"><span>Total balance</span><button className="quiet-button" onClick={reload}>Refresh ↻</button></div><strong className="total-balance">{money(data.balance.total_balance_cents)}</strong><div className="balance-meta"><span className="positive-dot" />Available to spend <strong>{money(data.balance.total_available_cents)}</strong></div><BalanceTrend transactions={data.transactions} total={data.balance.total_balance_cents} /></section><section className="quick-transfer"><div className="section-head"><div><p className="eyebrow">Move money</p><h2>Quick transfer</h2></div><span className="secure-chip">✦ Secure</span></div><form onSubmit={submit} className="transfer-form"><label>From<select><option>{data.accounts[0]?.account_type} · {data.accounts[0]?.account_number}</option></select></label><label>To<select value={selected} onChange={(e) => setSelected(e.target.value)} required><option value="">Choose a beneficiary</option>{data.beneficiaries.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.account_hint}</option>)}</select></label><div className="amount-input"><span>£</span><input inputMode="decimal" type="number" min="0.01" step="0.01" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} required /></div><input className="reference-input" placeholder="Reference (optional)" value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} /><button className="primary-button" type="submit" disabled={busy || !selected}>{busy ? <><span className="spinner" />Sending…</> : <>Send synthetic transfer <span>→</span></>}</button>{message && <div className={message.type === 'ok' ? 'success-note' : 'form-error'}>{message.text}</div>}</form><p className="transfer-footnote">Transfers are protected and can’t be sent twice accidentally.</p></section><section className="recent-section"><div className="section-head"><div><p className="eyebrow">Your money</p><h2>Recent activity</h2></div><button className="text-link text-button" onClick={openActivity}>View all <span>→</span></button></div><TransactionList transactions={data.transactions.slice(0, 4)} /></section><section className="accounts-mini"><div className="section-head"><div><p className="eyebrow">Across your accounts</p><h2>Accounts</h2></div><span className="account-count">{data.accounts.length} accounts</span></div>{data.accounts.map((account) => <div className="account-row" key={account.id}><div className="account-icon">{account.account_type === 'Savings' ? '◌' : '◍'}</div><div><strong>{account.account_type}</strong><span>{account.account_number}</span></div><div className="account-amount"><strong>{money(account.balance_cents)}</strong><span>{account.status}</span></div></div>)}</section></div>
}

function BalanceTrend({ transactions, total }: { transactions: Transaction[]; total: number }) {
  const ordered = [...transactions].sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  let running = total - ordered.reduce((sum, item) => sum + (item.direction === 'in' ? item.amount_cents : -item.amount_cents), 0);
  const points = [running, ...ordered.map(item => { running += item.direction === 'in' ? item.amount_cents : -item.amount_cents; return running; })];
  const low = Math.min(...points), range = Math.max(...points) - low || 1;
  const path = points.map((value, i) => `${i === 0 ? 'M' : 'L'}${i * 700 / Math.max(points.length - 1, 1)},${105 - (value - low) / range * 80}`).join(' ');
  return <div className="balance-chart"><span className="chart-label">Balance reconstructed from recorded activity</span><svg viewBox="0 0 700 120" preserveAspectRatio="none" role="img" aria-label="Synthetic balance trend derived from recorded transactions"><path d={`${path} L700,120 L0,120 Z`} fill="#b7d9c2" opacity=".12"/><path d={path} fill="none" stroke="#e6f2e6" strokeWidth="3"/></svg><div className="chart-axis"><span>{ordered.length ? dateLabel(ordered[0].occurred_at) : 'No activity'}</span><span>Current balance</span></div></div>;
}

function TransactionList({ transactions }: { transactions: Transaction[] }) { if (!transactions.length) return <EmptyState title="No activity yet" text="Your latest transactions will appear here." />; return <div className="transaction-list">{transactions.map((item) => <div className="transaction-row" key={item.id}><div className={`transaction-icon ${item.direction === 'in' ? 'in' : ''}`}>{item.direction === 'in' ? '↓' : '↑'}</div><div className="transaction-copy"><strong>{item.merchant}</strong><span>{item.description} · {dateLabel(item.occurred_at)}</span></div><strong className={`transaction-amount ${item.direction === 'in' ? 'income' : ''}`}>{item.direction === 'in' ? '+' : '−'}{money(item.amount_cents)}</strong></div>)}</div> }

function ActivityPage({ data }: { data: BankData }) { const [filter, setFilter] = useState('All activity'); const categories = ['All activity', ...Array.from(new Set(data.transactions.map((item) => item.category)))]; const filtered = filter === 'All activity' ? data.transactions : data.transactions.filter((item) => item.category === filter); return <section className="page-card"><div className="filter-row"><div><p className="eyebrow">A clear view of your money</p><h2>All activity</h2></div><select value={filter} onChange={(e) => setFilter(e.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select></div><TransactionList transactions={filtered} /></section> }
function AccountsPage({ data }: { data: BankData }) { return <div className="cards-grid">{data.accounts.map((account) => <article className="account-detail" key={account.id}><div className="account-detail-top"><div className="account-icon large">{account.account_type === 'Savings' ? '◌' : '◍'}</div><span className="status-pill">{account.status}</span></div><p className="eyebrow">{account.account_type}</p><h2>{money(account.balance_cents)}</h2><p>{account.account_number}</p><div className="detail-rule" /><div className="detail-footer"><span>Available</span><strong>{money(account.available_cents)}</strong></div></article>)}</div> }
function CardsPage({ cards }: { cards: Card[] }) { if (!cards.length) return <EmptyState title="No cards yet" text="Your cards will appear here when they are ready." />; return <div className="cards-grid">{cards.map((card, index) => <article className={`bank-card ${index % 2 ? 'card-light' : ''}`} key={card.id}><div className="bank-card-top"><span>phantombank</span><span>✦</span></div><div className="card-chip">▦</div><strong className="card-number">{card.card_number_masked}</strong><div className="bank-card-bottom"><span>{card.card_name}<small>{card.card_type}</small></span><span>EXP {card.expires_on}</span></div></article>)}</div> }
function ProfilePage({ profile }: { profile: Profile | null }) { if (!profile) return <EmptyState title="Profile unavailable" text="We could not find your profile details." />; return <section className="profile-card"><div className="profile-hero"><div className="profile-avatar">{initials(profile.full_name)}</div><div><p className="eyebrow">Personal details</p><h2>{profile.full_name}</h2><span>Customer since {new Date(profile.created_at).getFullYear()}</span></div></div><div className="profile-fields"><div><span>Email address</span><strong>{profile.email}</strong></div><div><span>Phone number</span><strong>{profile.phone}</strong></div><div><span>Home address</span><strong>{profile.address}</strong></div></div><p className="profile-note">These details are entirely synthetic. Profile editing is not available in this demonstration.</p></section> }
function SupportPage() { return <div className="support-grid"><section className="support-card support-main"><span className="support-spark">✦</span><p className="eyebrow">A fictional bank. A real protection flow.</p><h2>Banking, with a safety boundary.</h2><p>This demonstration contains only generated customers, balances and transactions. No financial institution or payment network is connected.</p><p>Browse accounts, filter activity, or send a synthetic transfer from the overview. Your ledger updates are persisted; repeating a request with the same idempotency key does not debit twice.</p></section><section className="support-card"><h3>When protection is unavailable</h3><p>The bank pauses protected operations instead of bypassing PhantomLayer. Retry once the local protection service has recovered.</p></section><section className="support-card"><h3>Demo support</h3><p>No live support desk or email delivery is connected. Support ticket management is future functionality. Ask the Rags2Riches demo operator for assistance.</p></section></div> }

export default App
