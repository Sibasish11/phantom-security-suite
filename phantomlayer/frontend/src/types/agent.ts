export type AgentStatus =
  | "pending"
  | "connecting"
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

export interface AgentRegistrationRequest {
  name: string;
  domain_id: string;
  version?: string;
  capabilities?: string[];
}

export interface AgentRegistrationResponse {
  agent_id: string;
  name: string;
  status: AgentStatus;
  registration_token: string;
}

export interface AgentHealth {
  status: AgentStatus;
  realDatabaseReachable: boolean;
  honeypotDatabaseReachable: boolean;
  telemetryConnected: boolean;
  lastHeartbeatAt: string | null;
}

export interface AgentDeploymentState {
  agent: Agent | null;
  registrationToken: string | null;

  isRegistering: boolean;
  isConnected: boolean;

  error: string | null;
}
