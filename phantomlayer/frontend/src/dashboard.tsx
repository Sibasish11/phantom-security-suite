  import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

const TOKEN_KEY = "phantomlayer_access_token";
const USER_KEY = "phantomlayer_user";

type User = {
  user_id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: string;
};

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

type Stats = {
  total_incidents: number;
  critical_incidents: number;
  high_risk_incidents: number;
  active_honeypot_sessions: number;
  active_honeypots: number;
  honeypot_interactions: number;
  requests_routed_to_honeypot: number;
  requests_routed_to_real: number;
  blocked_requests: number;
  attack_stages: Record<string, number>;
  top_triggered_rules: {
    rule: string;
    count: number;
  }[];
};

type SecurityEvent = {
  event_id: string;
  timestamp: string;
  operation?: string;
  session_id?: string;
  risk_score?: number;
  severity?: string;
  original_target?: string;
  final_target?: string;
  attack_stage?: string;
  event_type: string;
  triggered_rules?: string[];
  metadata?: Record<string, unknown>;
};

type IncidentSummary = {
  incident_id: string;
  session_id: string;
  severity: string;
  risk_score: number;
  attack_stage?: string;
  status: string;
  created_at: string;
  likely_objective?: string;
};

type IncidentDetail = {
  report_id?: string;
  incident_id?: string;
  session_id: string;
  created_at: string;
  status: string;

  sanitized_payload?: {
    session_id?: string;
    session_duration_seconds?: number;
    final_attack_stage?: string;
    total_interactions?: number;
    unique_operations?: string[];
    triggered_rule_names?: string[];
    max_risk_score?: number;
    avg_risk_score?: number;
    exposed_entity_counts?: Record<string, number>;
    correlated_event_count?: number;
    timeline?: {
      step: number;
      timestamp_utc: string;
      operation: string;
      risk_score: number;
      attack_stage: string;
      triggered_rule_names: string[];
      entities_exposed_counts: Record<string, number>;
      success: boolean;
    }[];
  };

  analysis?: {
    incident_summary?: string;
    attack_stage_progression?: string[];
    observed_behavior?: string;
    operations_performed?: string[];
    sensitive_resources_targeted?: string[];
    exposed_synthetic_entities?: Record<string, number>;
    risk_assessment?: string;
    suspicious_patterns?: {
      pattern_name: string;
      description: string;
      confidence: string;
    }[];
    likely_objective?: string;
    defensive_recommendations?: {
      action_type: string;
      description: string;
      priority: string;
    }[];
    limitations?: string;
    analysis_provider?: string;
  };

  error?: string | null;
};

type Domain = {
  id: string;
  domain: string;
  verification_record_name: string;
  verification_token: string;
  token_expires_at: string;
  verified: boolean;
  verified_at?: string | null;
};

type Agent = {
  agent_id: string;
  name: string;
  domain_id?: string | null;
  version: string;
  capabilities: string[];
  status: string;
  registered_at: string;
  last_heartbeat_at?: string | null;
  real_db_reachable?: boolean | null;
  honeypot_db_reachable?: boolean | null;
  telemetry_events_sent?: number;
};

type Protection = {
  id: string;
  organization_id?: string;
  domain_id: string;
  layer: string;
  status: string;
  enabled: boolean;
  configuration?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

type Page =
  | "overview"
  | "threats"
  | "sessions"
  | "events"
  | "ai"
  | "domains"
  | "protections"
  | "agents";

type ApiResult<T> = {
  data?: T;
  error?: string;
};

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();

  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearAuth();
    window.dispatchEvent(new Event("phantomlayer:logout"));
    throw new Error("Authentication expired");
  }

  const text = await response.text();

  if (!response.ok) {
    let detail = "";

    try {
      const parsed = JSON.parse(text);
      detail =
        parsed.detail ||
        parsed.message ||
        parsed.error ||
        "";
    } catch {
      detail = text;
    }

    throw new Error(
      `${response.status}${detail ? ` — ${detail}` : ""}`,
    );
  }

  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

function extractList<T>(value: unknown, keys: string[] = []): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (value && typeof value === "object") {
    const object = value as Record<string, unknown>;

    for (const key of keys) {
      if (Array.isArray(object[key])) {
        return object[key] as T[];
      }
    }
  }

  return [];
}

function label(value?: string): string {
  return (value || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatTime(value?: string): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRelative(value?: string): string {
  if (!value) return "—";

  const time = new Date(value).getTime();

  if (Number.isNaN(time)) return "—";

  const seconds = Math.max(
    0,
    Math.floor((Date.now() - time) / 1000),
  );

  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);

  if (hours < 24) return `${hours}h ago`;

  return `${Math.floor(hours / 24)}d ago`;
}

function severityFromRisk(risk = 0): string {
  if (risk >= 76) return "critical";
  if (risk >= 51) return "high";
  if (risk >= 31) return "medium";
  return "low";
}

function Badge({
  value,
  tone,
}: {
  value?: string;
  tone?: string;
}) {
  const resolved = tone || value || "neutral";

  return (
    <span className={`badge ${resolved.toLowerCase()}`}>
      {label(value || tone)}
    </span>
  );
}

function HexMark({
  small = false,
}: {
  small?: boolean;
}) {
  return (
    <div className={`hex-mark ${small ? "small" : ""}`}>
      <span />
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}

function Logo({
  compact = false,
}: {
  compact?: boolean;
}) {
  return (
    <div className={`brand ${compact ? "compact" : ""}`}>
      <HexMark small />
      <div>
        <strong>
          PHANTOM<span>LAYER</span>
        </strong>
        {!compact && <small>DECEPTION CONTROL PLANE</small>}
      </div>
    </div>
  );
}

function Login({
  onLogin,
}: {
  onLogin: (response: LoginResponse) => void;
}) {
  const [email, setEmail] = useState("admin@phantomdemo.com");
  const [password, setPassword] = useState("PhantomTest123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      });

      localStorage.setItem(
        TOKEN_KEY,
        response.access_token,
      );

      localStorage.setItem(
        USER_KEY,
        JSON.stringify(response.user),
      );

      onLogin(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-grid" />

      <div className="login-left">
        <Logo />

        <div className="login-hero">
          <div className="eyebrow">DEFENSIVE DECEPTION PLATFORM</div>

          <h1>
            Let attackers
            <br />
            <span>enter the wrong room.</span>
          </h1>

          <p>
            PhantomLayer detects suspicious behavior,
            calculates risk, and silently redirects
            attackers into controlled deception environments.
          </p>

          <div className="login-diagram">
            <div className="diagram-node">
              <span>01</span>
              <b>TRAFFIC</b>
              <small>incoming request</small>
            </div>

            <i />

            <div className="diagram-node active">
              <span>02</span>
              <b>PHANTOMLAYER</b>
              <small>detect · score · route</small>
            </div>

            <i />

            <div className="diagram-split">
              <div className="diagram-node safe">
                <span>03A</span>
                <b>REAL</b>
                <small>legitimate traffic</small>
              </div>

              <div className="diagram-node trap">
                <span>03B</span>
                <b>HONEYPOT</b>
                <small>attacker traffic</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="login-card-wrap">
        <div className="login-card">
          <div className="login-card-top">
            <div className="status-dot" />
            <span>CONTROL PLANE</span>
            <em>SECURE ACCESS</em>
          </div>

          <div className="login-title">
            <div className="mini-hive">
              <HexMark small />
            </div>

            <div>
              <div className="eyebrow">PHANTOMLAYER</div>
              <h2>Sign in to your hive</h2>
              <p>
                Access security telemetry,
                deception infrastructure and
                incident intelligence.
              </p>
            </div>
          </div>

          <form onSubmit={submit}>
            <label>
              WORK EMAIL
              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                autoComplete="email"
                required
              />
            </label>

            <label>
              PASSWORD
              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                autoComplete="current-password"
                required
              />
            </label>

            {error && (
              <div className="login-error">
                <strong>ACCESS DENIED</strong>
                <span>{error}</span>
              </div>
            )}

            <button
              className="login-button"
              type="submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  AUTHENTICATING...
                </>
              ) : (
                <>
                  ENTER HIVE
                  <span>→</span>
                </>
              )}
            </button>
          </form>

          <div className="login-footer">
            <span>
              <i className="tiny-green" />
              Control plane operational
            </span>
            <span>v0.1.0</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Sidebar({
  page,
  setPage,
  user,
  onLogout,
}: {
  page: Page;
  setPage: (page: Page) => void;
  user: User;
  onLogout: () => void;
}) {
  const groups = [
    {
      title: "COMMAND",
      items: [
        ["overview", "Hive Overview", "⌂"],
        ["threats", "Threats", "!"],
        ["sessions", "Attack Sessions", "◈"],
        ["events", "Security Events", "≋"],
      ],
    },
    {
      title: "INTELLIGENCE",
      items: [
        ["ai", "AI Analysis", "✦"],
      ],
    },
    {
      title: "DEFENSE",
      items: [
        ["domains", "Protected Domains", "◇"],
        ["protections", "Protection Layers", "⬡"],
        ["agents", "Hive Sentinels", "◉"],
      ],
    },
  ] as const;

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Logo />
      </div>

      <div className="hive-status">
        <span />
        HIVE ONLINE
      </div>

      <nav>
        {groups.map((group) => (
          <div className="nav-group" key={group.title}>
            <div className="nav-label">{group.title}</div>

            {group.items.map(([id, title, icon]) => (
              <button
                key={id}
                className={`nav-item ${
                  page === id ? "active" : ""
                }`}
                onClick={() => setPage(id)}
              >
                <span className="nav-icon">{icon}</span>
                <span>{title}</span>

                {id === "threats" && (
                  <b className="nav-count">!</b>
                )}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="engine-status">
          <div className="engine-icon">
            <HexMark small />
          </div>

          <div>
            <span>PROTECTION ENGINE</span>
            <strong>ACTIVE</strong>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="avatar">
            {(user.full_name || user.email)
              .charAt(0)
              .toUpperCase()}
          </div>

          <div>
            <strong>
              {user.full_name || "Administrator"}
            </strong>
            <span>{user.role}</span>
          </div>

          <button
            title="Sign out"
            onClick={onLogout}
          >
            ↗
          </button>
        </div>
      </div>
    </aside>
  );
}

function Topbar({
  page,
  user,
  onRefresh,
  refreshing,
}: {
  page: Page;
  user: User;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const titles: Record<Page, string> = {
    overview: "Hive Overview",
    threats: "Threat Intelligence",
    sessions: "Attack Sessions",
    events: "Security Events",
    ai: "AI Incident Analysis",
    domains: "Protected Domains",
    protections: "Protection Layers",
    agents: "Hive Sentinels",
  };

  return (
    <header className="topbar">
      <div>
        <div className="breadcrumbs">
          PHANTOMLAYER
          <span>/</span>
          SECURITY CONTROL PLANE
          <span>/</span>
          {page.toUpperCase()}
        </div>

        <h1>{titles[page]}</h1>
      </div>

      <div className="topbar-right">
        <div className="network-status">
          <span className="pulse green" />
          <div>
            <small>NETWORK STATUS</small>
            <strong>PROTECTED</strong>
          </div>
        </div>

        <div className="top-divider" />

        <div className="top-stat">
          <small>ACTIVE DECOYS</small>
          <strong>—</strong>
        </div>

        <div className="top-stat critical">
          <small>CRITICAL</small>
          <strong>—</strong>
        </div>

        <button
          className="refresh-button"
          onClick={onRefresh}
          disabled={refreshing}
        >
          <span className={refreshing ? "spin" : ""}>↻</span>
        </button>

        <div className="top-avatar">
          {(user.full_name || user.email)
            .charAt(0)
            .toUpperCase()}
        </div>
      </div>
    </header>
  );
}

function MetricCard({
  label: title,
  value,
  subtitle,
  icon,
  tone = "cyan",
}: {
  label: string;
  value: number | string;
  subtitle: string;
  icon: string;
  tone?: string;
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>

      <div className="metric-copy">
        <span>{title}</span>
        <strong>{value}</strong>
        <small>{subtitle}</small>
      </div>

      <div className="metric-glow" />
    </article>
  );
}

function HiveVisualization({
  stats,
}: {
  stats?: Stats;
}) {
  const cells = [
    {
      name: "EDGE GATEWAY",
      status: "PROTECTED",
      value: stats?.requests_routed_to_real || 0,
      type: "safe",
    },
    {
      name: "API DECOY",
      status:
        stats?.active_honeypot_sessions
          ? "ENGAGED"
          : "STANDBY",
      value: stats?.active_honeypot_sessions || 0,
      type:
        stats?.active_honeypot_sessions
          ? "danger"
          : "amber",
    },
    {
      name: "DATA VAULT",
      status:
        stats?.honeypot_interactions
          ? "INTERACTING"
          : "SEALED",
      value: stats?.honeypot_interactions || 0,
      type:
        stats?.honeypot_interactions
          ? "danger"
          : "cyan",
    },
    {
      name: "SESSION TRAP",
      status:
        stats?.active_honeypot_sessions
          ? "ACTIVE"
          : "READY",
      value: stats?.active_honeypot_sessions || 0,
      type: "amber",
    },
    {
      name: "AI OBSERVER",
      status:
        stats?.total_incidents
          ? "ANALYZING"
          : "READY",
      value: stats?.total_incidents || 0,
      type: "purple",
    },
    {
      name: "EVENT CORE",
      status: "RECORDING",
      value:
        (stats?.honeypot_interactions || 0) +
        (stats?.total_incidents || 0),
      type: "cyan",
    },
  ];

  return (
    <section className="panel hive-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">
            DECEPTION INFRASTRUCTURE
          </div>
          <h2>Phantom Hive</h2>
        </div>

        <div className="live-indicator">
          <span />
          LIVE TOPOLOGY
        </div>
      </div>

      <div className="hive-visual">
        <div className="orbit orbit-one" />
        <div className="orbit orbit-two" />

        <div className="hive-core">
          <div className="core-hex">
            <HexMark small />
          </div>

          <strong>PHANTOM</strong>
          <small>CONTROL</small>
        </div>

        <div className="hive-cells">
          {cells.map((cell, index) => (
            <div
              key={cell.name}
              className={`hive-cell ${cell.type}`}
            >
              <div className="cell-top">
                <span className="cell-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="cell-status">
                  {cell.status}
                </span>
              </div>

              <strong>{cell.name}</strong>

              <div className="cell-bottom">
                <span>ACTIVITY</span>
                <b>{cell.value}</b>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RoutingPanel({
  stats,
}: {
  stats?: Stats;
}) {
  const real = stats?.requests_routed_to_real || 0;
  const honey =
    stats?.requests_routed_to_honeypot || 0;
  const blocked = stats?.blocked_requests || 0;

  const total = real + honey + blocked;

  const deceptionRate =
    total > 0
      ? Math.round((honey / total) * 100)
      : 0;

  return (
    <section className="panel routing-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">
            TRAFFIC INTELLIGENCE
          </div>
          <h2>Hive Routing</h2>
        </div>

        <span className="panel-code">
          ROUTER / LIVE
        </span>
      </div>

      <div className="routing-flow">
        <div className="traffic-source">
          <div className="traffic-ring">
            <span>◎</span>
          </div>
          <small>INBOUND</small>
          <small>TRAFFIC</small>
        </div>

        <div className="flow-lines">
          <div className="flow-line safe">
            <span />
          </div>

          <div className="flow-line trap">
            <span />
          </div>

          <div className="flow-line blocked">
            <span />
          </div>
        </div>

        <div className="route-targets">
          <div className="route-target safe">
            <i>◆</i>
            <div>
              <strong>REAL</strong>
              <small>{real} requests</small>
            </div>
          </div>

          <div className="route-target trap">
            <i>⬡</i>
            <div>
              <strong>HONEYPOT</strong>
              <small>{honey} diverted</small>
            </div>
          </div>

          <div className="route-target blocked">
            <i>×</i>
            <div>
              <strong>BLOCKED</strong>
              <small>{blocked} stopped</small>
            </div>
          </div>
        </div>
      </div>

      <div className="deception-meter">
        <div>
          <span>DECEPTION RATE</span>
          <strong>{deceptionRate}%</strong>
        </div>

        <div className="meter">
          <span style={{ width: `${deceptionRate}%` }} />
        </div>

        <small>
          Suspicious traffic is silently absorbed by the
          deception layer.
        </small>
      </div>
    </section>
  );
}

function ThreatStream({
  events,
  incidents,
  onIncident,
}: {
  events: SecurityEvent[];
  incidents: IncidentSummary[];
  onIncident: (incident: IncidentSummary) => void;
}) {
  const merged = useMemo(() => {
    const eventItems = events.slice(0, 8);

    if (eventItems.length) {
      return eventItems;
    }

    return incidents.slice(0, 8).map((incident) => ({
      event_id: incident.incident_id,
      timestamp: incident.created_at,
      operation: incident.likely_objective || "security_event",
      session_id: incident.session_id,
      risk_score: incident.risk_score,
      severity: incident.severity,
      final_target: "honeypot",
      event_type: "incident",
      attack_stage: incident.attack_stage,
    }));
  }, [events, incidents]);

  if (!merged.length) {
    return (
      <section className="panel threat-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">LIVE FEED</div>
            <h2>Threat Stream</h2>
          </div>

          <div className="live-indicator">
            <span />
            LIVE
          </div>
        </div>

        <div className="empty-feed">
          <div className="empty-icon">⬡</div>
          <strong>The hive is quiet.</strong>
          <p>
            No suspicious activity has been observed.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel threat-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">LIVE FEED</div>
          <h2>Threat Stream</h2>
        </div>

        <div className="live-indicator">
          <span />
          LIVE
        </div>
      </div>

      <div className="event-list">
        {merged.map((event, index) => (
          <button
            className="event-row"
            key={event.event_id || index}
            onClick={() => {
              const incident = incidents.find(
                (item) =>
                  item.session_id ===
                  event.session_id,
              );

              if (incident) {
                onIncident(incident);
              }
            }}
          >
            <div
              className={`event-severity ${
                severityFromRisk(
                  event.risk_score || 0,
                )
              }`}
            />

            <div className="event-main">
              <strong>
                {label(event.operation)}
              </strong>

              <span>
                {event.session_id
                  ? event.session_id.slice(0, 18)
                  : "system event"}
              </span>
            </div>

            <Badge
              value={
                event.final_target ||
                event.severity ||
                "event"
              }
            />

            <div className="event-risk">
              <strong>
                {event.risk_score ?? 0}
              </strong>
              <span>RISK</span>
            </div>

            <time>
              {formatRelative(event.timestamp)}
            </time>

            <span className="event-arrow">›</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function ActivityPanel({
  events,
}: {
  events: SecurityEvent[];
}) {
  return (
    <section className="panel activity-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">TELEMETRY</div>
          <h2>Hive Activity</h2>
        </div>

        <span className="panel-code">
          {events.length} EVENTS
        </span>
      </div>

      {events.length ? (
        <div className="activity-list">
          {events.slice(0, 7).map((event, index) => (
            <div className="activity-row" key={event.event_id}>
              <span className="activity-line">
                {index !== events.length - 1 && <i />}
                <b />
              </span>

              <div>
                <strong>
                  {label(event.event_type)}
                </strong>
                <span>
                  {label(event.operation)}
                </span>
              </div>

              <Badge
                value={event.final_target || "unknown"}
              />

              <time>
                {formatTime(event.timestamp)}
              </time>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-small">
          Waiting for telemetry...
        </div>
      )}
    </section>
  );
}

function StatsBreakdown({
  stats,
}: {
  stats?: Stats;
}) {
  const stages = Object.entries(
    stats?.attack_stages || {},
  );

  const rules = stats?.top_triggered_rules || [];

  return (
    <div className="breakdown-grid">
      <section className="panel breakdown-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">
              ATTACK PROGRESSION
            </div>
            <h2>Attack Stages</h2>
          </div>
        </div>

        {stages.length ? (
          <div className="stage-list">
            {stages.map(([stage, count]) => (
              <div className="stage-row" key={stage}>
                <div className="stage-name">
                  <span />
                  {label(stage)}
                </div>

                <div className="stage-bar">
                  <span
                    style={{
                      width: `${Math.min(
                        100,
                        count * 12,
                      )}%`,
                    }}
                  />
                </div>

                <strong>{count}</strong>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-small">
            No attack progression observed.
          </div>
        )}
      </section>

      <section className="panel breakdown-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">
              DETECTION ENGINE
            </div>
            <h2>Triggered Rules</h2>
          </div>
        </div>

        {rules.length ? (
          <div className="rule-list">
            {rules.map((rule) => (
              <div className="rule-row" key={rule.rule}>
                <code>{rule.rule}</code>
                <span>{rule.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-small">
            No detection rules triggered.
          </div>
        )}
      </section>
    </div>
  );
}

function IncidentsTable({
  incidents,
  onSelect,
}: {
  incidents: IncidentSummary[];
  onSelect: (incident: IncidentSummary) => void;
}) {
  return (
    <section className="panel table-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">
            SECURITY OPERATIONS
          </div>
          <h2>Recent Incidents</h2>
        </div>

        <span className="panel-code">
          {incidents.length} TOTAL
        </span>
      </div>

      {!incidents.length ? (
        <div className="table-empty">
          <div>✓</div>
          <strong>No incidents detected</strong>
          <span>
            PhantomLayer has not observed suspicious
            activity in the current telemetry window.
          </span>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Incident</th>
                <th>Severity</th>
                <th>Risk</th>
                <th>Session</th>
                <th>Attack Stage</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>

            <tbody>
              {incidents.map((incident) => (
                <tr
                  key={incident.incident_id}
                  onClick={() => onSelect(incident)}
                >
                  <td>
                    <strong>
                      #{incident.incident_id.slice(0, 8)}
                    </strong>
                  </td>

                  <td>
                    <Badge value={incident.severity} />
                  </td>

                  <td>
                    <div className="risk-value">
                      <span>
                        {incident.risk_score}
                      </span>
                      <div>
                        <i
                          style={{
                            width: `${incident.risk_score}%`,
                          }}
                        />
                      </div>
                    </div>
                  </td>

                  <td>
                    <code>
                      {incident.session_id.slice(0, 18)}
                    </code>
                  </td>

                  <td>
                    {label(incident.attack_stage)}
                  </td>

                  <td>
                    <Badge
                      value={incident.status}
                    />
                  </td>

                  <td>
                    {formatTime(incident.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function IncidentDrawer({
  incident,
  detail,
  onClose,
}: {
  incident: IncidentSummary;
  detail?: IncidentDetail;
  onClose: () => void;
}) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        className="incident-drawer"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="drawer-close"
          onClick={onClose}
        >
          ×
        </button>

        <div className="eyebrow">
          INCIDENT DETAIL
        </div>

        <h2>
          #{incident.incident_id.slice(0, 8)}
        </h2>

        <div className="drawer-meta">
          <Badge value={incident.severity} />
          <span>Risk {incident.risk_score}</span>
          <span>{label(incident.status)}</span>
        </div>

        <div className="drawer-risk">
          <div className="risk-circle">
            <strong>{incident.risk_score}</strong>
            <span>RISK</span>
          </div>

          <div>
            <small>ATTACK STAGE</small>
            <strong>
              {label(
                incident.attack_stage ||
                  detail?.sanitized_payload
                    ?.final_attack_stage,
              )}
            </strong>
          </div>
        </div>

        <section>
          <div className="drawer-label">
            SESSION
          </div>

          <code className="session-code">
            {incident.session_id}
          </code>
        </section>

        <section>
          <div className="drawer-label">
            INCIDENT SUMMARY
          </div>

          <p className="drawer-copy">
            {detail?.analysis?.incident_summary ||
              incident.likely_objective ||
              "Analysis is not available for this incident yet."}
          </p>
        </section>

        <section>
          <div className="drawer-label">
            OBSERVED OPERATIONS
          </div>

          <div className="operation-chips">
            {(
              detail?.sanitized_payload
                ?.unique_operations || []
            ).map((operation) => (
              <span key={operation}>
                {label(operation)}
              </span>
            ))}

            {!detail?.sanitized_payload
              ?.unique_operations?.length && (
              <span>
                {label(incident.likely_objective)}
              </span>
            )}
          </div>
        </section>

        <section>
          <div className="drawer-label">
            DEFENSIVE RECOMMENDATIONS
          </div>

          <div className="recommendations">
            {detail?.analysis
              ?.defensive_recommendations
              ?.length ? (
              detail.analysis.defensive_recommendations.map(
                (recommendation) => (
                  <div
                    className="recommendation"
                    key={recommendation.description}
                  >
                    <Badge
                      value={
                        recommendation.priority
                      }
                    />

                    <span>
                      {recommendation.description}
                    </span>
                  </div>
                ),
              )
            ) : (
              <div className="recommendation">
                <Badge value="review" />
                <span>
                  Review the incident and associated
                  telemetry.
                </span>
              </div>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}

function ModulePage({
  page,
  stats,
  events,
  incidents,
  domains,
  agents,
  protections,
  onIncident,
}: {
  page: Page;
  stats?: Stats;
  events: SecurityEvent[];
  incidents: IncidentSummary[];
  domains: Domain[];
  agents: Agent[];
  protections: Protection[];
  onIncident: (incident: IncidentSummary) => void;
}) {
  if (page === "overview") {
    return null;
  }

  if (page === "threats") {
    const threats = incidents.filter(
      (incident) =>
        incident.severity === "critical" ||
        incident.severity === "high",
    );

    return (
      <div className="module-page">
        <div className="module-hero red">
          <div>
            <div className="eyebrow">
              THREAT INTELLIGENCE
            </div>
            <h2>Threat Command</h2>
            <p>
              High-risk activity observed by the
              PhantomLayer detection engine.
            </p>
          </div>

          <div className="module-big-number">
            {stats?.high_risk_incidents || 0}
            <span>HIGH RISK</span>
          </div>
        </div>

        <ThreatStream
          events={events}
          incidents={threats}
          onIncident={onIncident}
        />
      </div>
    );
  }

  if (page === "sessions") {
    const sessions = Array.from(
      new Map(
        events
          .filter((event) => event.session_id)
          .map((event) => [
            event.session_id,
            event,
          ]),
      ).values(),
    );

    return (
      <div className="module-page">
        <ModuleTitle
          eyebrow="ATTACK TRACKING"
          title="Attack Sessions"
          description="Correlated attacker activity grouped by session."
        />

        <section className="panel data-panel">
          {sessions.length ? (
            <div className="session-grid">
              {sessions.map((session) => (
                <div
                  className="session-card"
                  key={session.session_id}
                >
                  <div className="session-card-top">
                    <span className="session-live">
                      ● ACTIVE
                    </span>
                    <Badge
                      value={
                        session.final_target ||
                        "honeypot"
                      }
                    />
                  </div>

                  <code>
                    {session.session_id}
                  </code>

                  <div className="session-details">
                    <div>
                      <span>LAST OPERATION</span>
                      <strong>
                        {label(session.operation)}
                      </strong>
                    </div>

                    <div>
                      <span>RISK</span>
                      <strong>
                        {session.risk_score ?? 0}
                      </strong>
                    </div>

                    <div>
                      <span>STAGE</span>
                      <strong>
                        {label(
                          session.attack_stage,
                        )}
                      </strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="◈"
              title="No attack sessions"
              description="Correlated attacker sessions will appear here when the hive observes suspicious activity."
            />
          )}
        </section>
      </div>
    );
  }

  if (page === "events") {
    return (
      <div className="module-page">
        <ModuleTitle
          eyebrow="TELEMETRY"
          title="Security Events"
          description="Raw security activity collected by the PhantomLayer control plane."
        />

        <section className="panel data-panel">
          {events.length ? (
            <div className="full-event-list">
              {events.map((event) => (
                <div
                  className="full-event"
                  key={event.event_id}
                >
                  <div className="event-time">
                    {formatTime(event.timestamp)}
                  </div>

                  <div
                    className={`event-severity ${
                      severityFromRisk(
                        event.risk_score || 0,
                      )
                    }`}
                  />

                  <div className="full-event-main">
                    <strong>
                      {label(event.event_type)}
                    </strong>

                    <span>
                      {label(event.operation)}
                    </span>
                  </div>

                  <Badge
                    value={
                      event.final_target ||
                      "unknown"
                    }
                  />

                  <span className="event-score">
                    {event.risk_score ?? 0}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="≋"
              title="No security events"
              description="Telemetry will appear here as the agent reports activity."
            />
          )}
        </section>
      </div>
    );
  }

  if (page === "ai") {
    return (
      <div className="module-page">
        <div className="module-hero purple">
          <div>
            <div className="eyebrow">
              ARTIFICIAL INTELLIGENCE
            </div>
            <h2>Incident Intelligence</h2>
            <p>
              AI-assisted analysis runs on sanitized
              security telemetry after deterministic
              detection and routing.
            </p>
          </div>

          <div className="ai-orb">
            <span>AI</span>
          </div>
        </div>

        <section className="panel data-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                ANALYSIS QUEUE
              </div>
              <h2>Recent Incidents</h2>
            </div>
          </div>

          {incidents.length ? (
            <div className="ai-list">
              {incidents.map((incident) => (
                <button
                  className="ai-incident"
                  key={incident.incident_id}
                  onClick={() => onIncident(incident)}
                >
                  <div className="ai-score">
                    {incident.risk_score}
                  </div>

                  <div>
                    <strong>
                      Incident #
                      {incident.incident_id.slice(
                        0,
                        8,
                      )}
                    </strong>

                    <span>
                      {label(
                        incident.attack_stage,
                      )}{" "}
                      ·{" "}
                      {label(
                        incident.likely_objective,
                      )}
                    </span>
                  </div>

                  <Badge
                    value={incident.severity}
                  />

                  <span className="event-arrow">
                    →
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="✦"
              title="No incidents awaiting analysis"
              description="When PhantomLayer correlates suspicious activity, AI analysis will appear here."
            />
          )}
        </section>
      </div>
    );
  }

  if (page === "domains") {
    return (
      <div className="module-page">
        <ModuleTitle
          eyebrow="CUSTOMER INFRASTRUCTURE"
          title="Protected Domains"
          description="Verified domains connected to this PhantomLayer organization."
        />

        <div className="resource-grid">
          {domains.map((domain) => (
            <div className="resource-card" key={domain.id}>
              <div className="resource-icon">◇</div>

              <div className="resource-card-head">
                <div>
                  <span>DOMAIN</span>
                  <h3>{domain.domain}</h3>
                </div>

                <Badge
                  value={
                    domain.verified
                      ? "verified"
                      : "pending"
                  }
                />
              </div>

              <div className="resource-meta">
                <span>
                  Verification record
                </span>
                <code>
                  {domain.verification_record_name}
                </code>
              </div>

              <div className="resource-meta">
                <span>Status</span>
                <strong>
                  {domain.verified
                    ? "Ownership verified"
                    : "Awaiting verification"}
                </strong>
              </div>
            </div>
          ))}

          {!domains.length && (
            <EmptyState
              icon="◇"
              title="No domains connected"
              description="Verified customer domains will appear here."
            />
          )}
        </div>
      </div>
    );
  }

  if (page === "protections") {
    return (
      <div className="module-page">
        <ModuleTitle
          eyebrow="DECEPTION CONFIGURATION"
          title="Protection Layers"
          description="Security layers currently configured for your protected infrastructure."
        />

        <div className="resource-grid">
          {protections.map((protection) => (
            <div
              className="resource-card protection-card"
              key={protection.id}
            >
              <div className="layer-visual">
                <HexMark small />
              </div>

              <div className="resource-card-head">
                <div>
                  <span>PROTECTION LAYER</span>
                  <h3>
                    {label(protection.layer)}
                  </h3>
                </div>

                <Badge
                  value={
                    protection.enabled
                      ? protection.status
                      : "disabled"
                  }
                />
              </div>

              <div className="resource-meta">
                <span>Configuration</span>
                <code>
                  {JSON.stringify(
                    protection.configuration || {},
                  )}
                </code>
              </div>

              <div className="active-line">
                <span />
                {protection.enabled
                  ? "PROTECTION ACTIVE"
                  : "PROTECTION DISABLED"}
              </div>
            </div>
          ))}

          {!protections.length && (
            <EmptyState
              icon="⬡"
              title="No protection layers"
              description="Protection configurations will appear after a domain is connected."
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="module-page">
      <ModuleTitle
        eyebrow="CUSTOMER DEPLOYMENT"
        title="Hive Sentinels"
        description="PhantomLayer agents deployed inside customer infrastructure."
      />

      <div className="resource-grid">
        {agents.map((agent) => (
          <div
            className="resource-card agent-card"
            key={agent.agent_id}
          >
            <div className="agent-status">
              <span
                className={
                  agent.status === "healthy"
                    ? "green"
                    : "amber"
                }
              />
              {label(agent.status)}
            </div>

            <div className="agent-title">
              <div className="agent-icon">
                ◉
              </div>

              <div>
                <span>SENTINEL</span>
                <h3>{agent.name}</h3>
              </div>
            </div>

            <code className="agent-id">
              {agent.agent_id}
            </code>

            <div className="agent-grid">
              <div>
                <span>VERSION</span>
                <strong>{agent.version}</strong>
              </div>

              <div>
                <span>TELEMETRY</span>
                <strong>
                  {agent.telemetry_events_sent || 0}
                </strong>
              </div>

              <div>
                <span>REAL DB</span>
                <strong>
                  {agent.real_db_reachable
                    ? "ONLINE"
                    : "—"}
                </strong>
              </div>

              <div>
                <span>HONEYPOT</span>
                <strong>
                  {agent.honeypot_db_reachable
                    ? "ONLINE"
                    : "—"}
                </strong>
              </div>
            </div>

            <div className="heartbeat">
              Last heartbeat{" "}
              {formatRelative(
                agent.last_heartbeat_at || undefined,
              )}
            </div>
          </div>
        ))}

        {!agents.length && (
          <EmptyState
            icon="◉"
            title="No sentinels connected"
            description="Deploy the PhantomLayer agent inside customer infrastructure to activate protection."
          />
        )}
      </div>
    </div>
  );
}

function ModuleTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="module-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      <div className="module-mark">
        <HexMark small />
      </div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state">
      <div>{icon}</div>
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

export function App() {
  const [user, setUser] = useState<User | null>(
    getStoredUser,
  );

  const [page, setPage] =
    useState<Page>("overview");

  const [stats, setStats] = useState<Stats>();
  const [events, setEvents] = useState<SecurityEvent[]>(
    [],
  );
  const [incidents, setIncidents] = useState<
    IncidentSummary[]
  >([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [protections, setProtections] = useState<
    Protection[]
  >([]);

  const [selectedIncident, setSelectedIncident] =
    useState<IncidentSummary>();

  const [incidentDetail, setIncidentDetail] =
    useState<IncidentDetail>();

  const [refreshing, setRefreshing] =
    useState(false);

  const [apiWarnings, setApiWarnings] = useState<
    string[]
  >([]);

  async function loadDashboard() {
    if (!getToken()) return;

    setRefreshing(true);

    const warnings: string[] = [];

    const [
      statsResult,
      incidentsResult,
      eventsResult,
      domainsResult,
      agentsResult,
      protectionsResult,
    ] = await Promise.all([
      api<Stats>("/security/stats")
        .then((data) => ({ data }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Stats unavailable",
        })),

      api<unknown>("/incidents")
        .then((data) => ({
          data: extractList<IncidentSummary>(
            data,
            ["incidents", "items", "results"],
          ),
        }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Incidents unavailable",
        })),

      api<unknown>("/security/events/recent")
        .then((data) => ({
          data: extractList<SecurityEvent>(
            data,
            ["events", "items", "results"],
          ),
        }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Events unavailable",
        })),

      api<unknown>("/domains")
        .then((data) => ({
          data: extractList<Domain>(
            data,
            ["domains", "items", "results"],
          ),
        }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Domains unavailable",
        })),

      api<unknown>("/agents")
        .then((data) => ({
          data: extractList<Agent>(
            data,
            ["agents", "items", "results"],
          ),
        }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Agents unavailable",
        })),

      api<unknown>("/protections")
        .then((data) => ({
          data: extractList<Protection>(
            data,
            ["protections", "items", "results"],
          ),
        }))
        .catch((error) => ({
          error:
            error instanceof Error
              ? error.message
              : "Protections unavailable",
        })),
    ]);

    if ("data" in statsResult && statsResult.data) {
      setStats(statsResult.data);
    } else if ("error" in statsResult) {
      warnings.push(`Telemetry: ${statsResult.error}`);
    }

    if (
      "data" in incidentsResult &&
      incidentsResult.data
    ) {
      setIncidents(incidentsResult.data);
    } else if ("error" in incidentsResult) {
      warnings.push(
        `Incidents: ${incidentsResult.error}`,
      );
    }

    if ("data" in eventsResult && eventsResult.data) {
      setEvents(eventsResult.data);
    } else if ("error" in eventsResult) {
      warnings.push(
        `Events: ${eventsResult.error}`,
      );
    }

    if (
      "data" in domainsResult &&
      domainsResult.data
    ) {
      setDomains(domainsResult.data);
    }

    if (
      "data" in agentsResult &&
      agentsResult.data
    ) {
      setAgents(agentsResult.data);
    }

    if (
      "data" in protectionsResult &&
      protectionsResult.data
    ) {
      setProtections(protectionsResult.data);
    }

    setApiWarnings(warnings);
    setRefreshing(false);
  }

  async function openIncident(
    incident: IncidentSummary,
  ) {
    setSelectedIncident(incident);
    setIncidentDetail(undefined);

    try {
      const detail = await api<IncidentDetail>(
        `/incidents/${incident.incident_id}`,
      );

      setIncidentDetail(detail);
    } catch {
      // Drawer still shows the incident summary.
    }
  }

  function logout() {
    clearAuth();
    setUser(null);
    setPage("overview");
  }

  useEffect(() => {
    const handleLogout = () => {
      setUser(null);
    };

    window.addEventListener(
      "phantomlayer:logout",
      handleLogout,
    );

    return () =>
      window.removeEventListener(
        "phantomlayer:logout",
        handleLogout,
      );
  }, []);

  useEffect(() => {
    if (!user) return;

    void loadDashboard();

    const interval = window.setInterval(
      () => void loadDashboard(),
      15000,
    );

    return () => window.clearInterval(interval);
  }, [user]);

  if (!user) {
    return (
      <Login
        onLogin={(response) => {
          setUser(response.user);
        }}
      />
    );
  }

  const overview = (
    <>
      <div className="hero-banner">
        <div>
          <div className="eyebrow">
            DECEPTION INFRASTRUCTURE
          </div>

          <h2>
            Your hive is{" "}
            <span>watching.</span>
          </h2>

          <p>
            PhantomLayer is monitoring protected
            infrastructure and silently redirecting
            suspicious activity into controlled
            deception environments.
          </p>

          <div className="hero-tags">
            <span>
              <i />
              DETECTION ACTIVE
            </span>

            <span>
              <i />
              SMART ROUTING
            </span>

            <span>
              <i />
              AI READY
            </span>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-orbit orbit-a" />
          <div className="hero-orbit orbit-b" />

          <div className="hero-core">
            <HexMark small />
            <span>PHANTOM</span>
          </div>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard
          label="Active Threats"
          value={stats?.total_incidents || 0}
          subtitle="incidents observed"
          icon="!"
          tone="red"
        />

        <MetricCard
          label="Critical Risk"
          value={stats?.critical_incidents || 0}
          subtitle="requires attention"
          icon="◆"
          tone="purple"
        />

        <MetricCard
          label="Honeypot Sessions"
          value={
            stats?.active_honeypot_sessions || 0
          }
          subtitle="intruders contained"
          icon="⬡"
          tone="amber"
        />

        <MetricCard
          label="Deception Hits"
          value={
            stats?.honeypot_interactions || 0
          }
          subtitle="synthetic interactions"
          icon="◇"
          tone="cyan"
        />

        <MetricCard
          label="Real Traffic"
          value={
            stats?.requests_routed_to_real || 0
          }
          subtitle="clean requests passed"
          icon="✓"
          tone="green"
        />
      </div>

      <div className="main-grid">
        <ThreatStream
          events={events}
          incidents={incidents}
          onIncident={openIncident}
        />

        <RoutingPanel stats={stats} />
      </div>

      <div className="main-grid lower-grid">
        <ActivityPanel events={events} />
        <HiveVisualization stats={stats} />
      </div>

      <StatsBreakdown stats={stats} />

      <IncidentsTable
        incidents={incidents}
        onSelect={openIncident}
      />
    </>
  );

  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        setPage={setPage}
        user={user}
        onLogout={logout}
      />

      <div className="app-main">
        <Topbar
          page={page}
          user={user}
          onRefresh={() => void loadDashboard()}
          refreshing={refreshing}
        />

        <main className="content">
          {apiWarnings.length > 0 && (
            <div className="soft-warning">
              <span>⚠</span>

              <div>
                <strong>
                  Some telemetry sources are unavailable
                </strong>

                <small>
                  The interface remains operational.
                  Available security data is still shown.
                </small>
              </div>

              <button
                onClick={() => setApiWarnings([])}
              >
                ×
              </button>
            </div>
          )}

          {page === "overview" ? (
            overview
          ) : (
            <ModulePage
              page={page}
              stats={stats}
              events={events}
              incidents={incidents}
              domains={domains}
              agents={agents}
              protections={protections}
              onIncident={openIncident}
            />
          )}
        </main>
      </div>

      {selectedIncident && (
        <IncidentDrawer
          incident={selectedIncident}
          detail={incidentDetail}
          onClose={() => {
            setSelectedIncident(undefined);
            setIncidentDetail(undefined);
          }}
        />
      )}
    </div>
  );
}