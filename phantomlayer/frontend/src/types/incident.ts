export type IncidentSeverity =
  | "low"
  | "medium"
  | "high"
  | "critical"
  | string;

export type IncidentStatus =
  | "open"
  | "investigating"
  | "resolved"
  | "closed"
  | string;

export type AttackStage =
  | "unknown"
  | "probing"
  | "reconnaissance"
  | "enumeration"
  | "credential_discovery"
  | "data_discovery"
  | "exploitation"
  | "lateral_movement"
  | "persistence"
  | "exfiltration"
  | "suspicious_activity"
  | string;

export interface Incident {
  id: string;

  session_id?: string | null;

  title?: string;
  summary?: string;

  severity?: IncidentSeverity;
  status?: IncidentStatus;

  risk_score?: number;
  attack_stage?: AttackStage;

  created_at?: string;
  updated_at?: string;

  event_count?: number;
  interaction_count?: number;

  source_ip?: string | null;

  [key: string]: unknown;
}

export interface IncidentTimelineEvent {
  id?: string;

  event_id?: string;
  session_id?: string | null;

  event_type?: string;
  operation?: string;

  original_target?: string;
  final_target?: string;

  risk_score: number;
  severity: string;
  suspicious: boolean;

  attack_stage?: AttackStage | null;

  interaction_count?: number | null;

  triggered_rules?: string[];

  timestamp: string;

  metadata?: Record<string, unknown>;
}

export interface IncidentTimeline {
  incident?: Incident;
  events: IncidentTimelineEvent[];
}

export interface IncidentAnalysis {
  incident_id?: string;
  session_id?: string;

  summary?: string;
  threat_level?: string;
  attack_stage?: AttackStage;

  confidence?: number;

  attacker_objective?: string;
  observed_behavior?: string[];

  indicators?: string[];

  recommended_actions?: string[];

  generated_at?: string;

  [key: string]: unknown;
}

export interface IncidentState {
  incidents: Incident[];
  selectedIncident: Incident | null;
  timeline: IncidentTimeline | null;
  analysis: IncidentAnalysis | null;

  isLoading: boolean;
  isAnalyzing: boolean;

  error: string | null;
}