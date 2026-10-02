export type SecuritySeverity =
  | "low"
  | "medium"
  | "high"
  | "critical"
  | string;

export type SecurityTarget =
  | "real"
  | "honeypot"
  | string;

export interface SecurityEvent {
  id?: string;
  event_id?: string;

  agent_id?: string;
  session_id?: string | null;

  event_type?: string;
  operation?: string;

  original_target?: SecurityTarget;
  final_target?: SecurityTarget;

  risk_score: number;
  severity: SecuritySeverity;

  suspicious: boolean;

  attack_stage?: string | null;
  interaction_count?: number | null;

  triggered_rules?: string[];

  timestamp: string;

  metadata?: Record<string, unknown>;
}

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

export interface RiskBreakdown {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface TargetBreakdown {
  real: number;
  honeypot: number;
}

export interface AttackStageBreakdown {
  stage: string;
  count: number;
}

export interface SecurityDashboardData {
  stats: SecurityStats;
  recentEvents: SecurityEvent[];

  riskBreakdown?: RiskBreakdown;
  targetBreakdown?: TargetBreakdown;
  attackStages?: AttackStageBreakdown[];
}

export interface SecurityFilter {
  severity?: SecuritySeverity;
  target?: SecurityTarget;
  suspicious?: boolean;
  attackStage?: string;
  sessionId?: string;
  search?: string;
}

export interface SecurityState {
  stats: SecurityStats | null;
  events: SecurityEvent[];

  isLoading: boolean;
  isRefreshing: boolean;

  error: string | null;
}