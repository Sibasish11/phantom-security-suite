const API_BASE_URL = "";

type ApiOptions = RequestInit & {
  token?: string | null;
};

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  return await response.text();
}

async function request<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { token, headers, ...fetchOptions } = options;

  const requestHeaders = new Headers(headers);

  if (!requestHeaders.has("Content-Type") && fetchOptions.body) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const accessToken =
    token ?? localStorage.getItem("phantomlayer_access_token");

  if (accessToken) {
    requestHeaders.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...fetchOptions,
      headers: requestHeaders,
    },
  );

  const data = await parseResponse(response);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data
    ) {
      const detail = (data as { detail?: unknown }).detail;

      if (typeof detail === "string") {
        message = detail;
      } else if (detail !== undefined) {
        message = JSON.stringify(detail);
      }
    }

    throw new ApiError(
      message,
      response.status,
      data,
    );
  }

  return data as T;
}

/* =========================================================
   Generic HTTP helpers
========================================================= */

export function apiGet<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "GET",
  });
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  options: ApiOptions = {},
): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "POST",
    body:
      body === undefined
        ? undefined
        : JSON.stringify(body),
  });
}

export function apiPatch<T>(
  path: string,
  body?: unknown,
  options: ApiOptions = {},
): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "PATCH",
    body:
      body === undefined
        ? undefined
        : JSON.stringify(body),
  });
}

export function apiDelete<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "DELETE",
  });
}

/* =========================================================
   Authentication
========================================================= */

export interface RegisterRequest {
  organization_name: string;
  full_name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: { user_id: string; organization_id: string; email: string; full_name: string; role: string };
  organization_name?: string;
}

export function register(
  payload: RegisterRequest,
): Promise<AuthResponse> {
  return apiPost<AuthResponse>(
    "/auth/register",
    { company_name: payload.organization_name, full_name: payload.full_name, email: payload.email, password: payload.password },
  );
}

export function login(
  payload: LoginRequest,
): Promise<AuthResponse> {
  return apiPost<AuthResponse>(
    "/auth/login",
    payload,
  );
}

/* =========================================================
   Organization / Domains
========================================================= */

export interface Domain {
  id: string;
  domain: string;
  verification_record_name: string;
  verification_token: string;
  token_expires_at: string;
  verified: boolean;
  verified_at: string | null;
}

export function getDomains(): Promise<Domain[]> {
  return apiGet<Domain[]>("/domains");
}

export function createDomain(
  domain: string,
): Promise<Domain> {
  return apiPost<Domain>("/domains", {
    domain,
  });
}

export function getDomain(
  domainId: string,
): Promise<Domain> {
  return apiGet<Domain>(
    `/domains/${domainId}`,
  );
}

export function verifyDomain(
  domainId: string,
): Promise<Domain> {
  return apiPost<Domain>(
    `/domains/${domainId}/verify`,
  );
}

export function demoVerifyDomain(
  domainId: string,
): Promise<Domain> {
  return apiPost<Domain>(
    `/domains/${domainId}/demo-verify`,
  );
}

/* =========================================================
   Protections
========================================================= */

export type ProtectionLayer =
  | "api"
  | "database"
  | "internal"
  | "full";

export type ProtectionStatus =
  | "configuring"
  | "active"
  | "paused";

export interface Protection {
  id: string;
  organization_id: string;
  domain_id: string;
  layer: ProtectionLayer;
  status: ProtectionStatus;
  enabled: boolean;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export function getProtections(): Promise<Protection[]> {
  return apiGet<Protection[]>("/protections");
}

export function getProtection(
  protectionId: string,
): Promise<Protection> {
  return apiGet<Protection>(
    `/protections/${protectionId}`,
  );
}

export function createProtection(payload: {
  domain_id: string;
  layer: ProtectionLayer;
  configuration?: Record<string, unknown>;
}): Promise<Protection> {
  return apiPost<Protection>(
    "/protections",
    payload,
  );
}

export function updateProtection(
  protectionId: string,
  payload: {
    layer?: ProtectionLayer;
    enabled?: boolean;
    status?: ProtectionStatus;
    configuration?: Record<string, unknown>;
  },
): Promise<Protection> {
  return apiPatch<Protection>(
    `/protections/${protectionId}`,
    payload,
  );
}

/* =========================================================
   Agents
========================================================= */

export type AgentStatus =
  | "pending"
  | "healthy"
  | "degraded"
  | "offline";

export interface Agent {
  agent_id: string;
  name: string;
  domain_id: string;
  version: string;
  capabilities: string[];
  status: AgentStatus;
  registered_at: string;
  last_heartbeat_at: string | null;
  real_db_reachable: boolean;
  honeypot_db_reachable: boolean;
  telemetry_events_sent: number;
}

export interface AgentRegistrationResponse {
  agent_id: string;
  name: string;
  status: AgentStatus;
  registration_token: string;
}

export function getAgents(): Promise<Agent[]> {
  return apiGet<Agent[]>("/agents");
}

export function getAgent(
  agentId: string,
): Promise<Agent> {
  return apiGet<Agent>(
    `/agents/${agentId}`,
  );
}

export function registerAgent(payload: {
  name: string;
  domain_id: string;
  version?: string;
  capabilities?: string[];
}): Promise<AgentRegistrationResponse> {
  return apiPost<AgentRegistrationResponse>(
    "/agents/register",
    payload,
  );
}

export function rotateAgentToken(
  agentId: string,
): Promise<{ registration_token: string }> {
  return apiPost<{ registration_token: string }>(
    `/agents/${agentId}/rotate-token`,
  );
}

/* =========================================================
   Security dashboard
========================================================= */

export interface SecurityStats {
  total_events: number;
  suspicious_events: number;
  active_sessions: number;
  critical_events: number;
  high_events: number;
  medium_events: number;
  low_events: number;
  honeypot_events: number;
  real_events: number;
}

export interface SecurityEvent {
  id?: string;
  event_id?: string;
  agent_id?: string;
  session_id?: string | null;
  event_type?: string;
  operation?: string;
  original_target?: string;
  final_target?: string;
  risk_score: number;
  severity: string;
  suspicious: boolean;
  attack_stage?: string | null;
  interaction_count?: number | null;
  triggered_rules?: string[];
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface Incident {
  id: string;
  session_id?: string;
  status?: string;
  severity?: string;
  risk_score?: number;
  attack_stage?: string;
  title?: string;
  summary?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export function getSecurityStats(): Promise<SecurityStats> {
  return apiGet<SecurityStats>(
    "/security/stats",
  );
}

export function getSecurityEvents(
  limit = 100,
): Promise<SecurityEvent[]> {
  return apiGet<SecurityEvent[]>(
    `/security/events?limit=${limit}`,
  );
}

export function getRecentSecurityEvents(
  limit = 50,
): Promise<SecurityEvent[]> {
  return apiGet<SecurityEvent[]>(
    `/security/events/recent?limit=${limit}`,
  );
}

export function getIncidents(): Promise<Incident[]> {
  return apiGet<Incident[]>("/incidents");
}

export async function getIncident(
  incidentId: string,
): Promise<Incident> {
  const detail = await apiGet<Incident>(
    `/incidents/${encodeURIComponent(incidentId)}`,
  );
  const summary = detail.summary && typeof detail.summary === "object"
    ? detail.summary as Record<string, unknown>
    : {};
  const payload = detail.sanitized_payload && typeof detail.sanitized_payload === "object"
    ? detail.sanitized_payload as Record<string, unknown>
    : {};
  return {
    ...detail,
    ...summary,
    operations_observed: payload.unique_operations ?? [],
    triggered_rules: payload.triggered_rule_names ?? [],
    exposed_synthetic_entities: payload.exposed_entity_counts ?? {},
  } as Incident;
}

export function getIncidentTimeline(
  incidentId: string,
): Promise<unknown> {
  return apiGet(
    `/incidents/${encodeURIComponent(incidentId)}/timeline`,
  );
}

export function analyzeIncident(
  sessionId: string,
  force = false,
): Promise<unknown> {
  return apiPost(
    `/api/v1/incidents/${encodeURIComponent(sessionId)}/analyze`,
    { force_reanalysis: force },
  );
}

/* =========================================================
   Health
========================================================= */

export interface HealthResponse {
  status: string;
  service?: string;
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}

/* =========================================================
   Logout helper
========================================================= */

export function clearAuthentication(): void {
  localStorage.removeItem(
    "phantomlayer_access_token",
  );

  localStorage.removeItem(
    "phantomlayer_user",
  );

  localStorage.removeItem(
    "phantomlayer_organization",
  );
}