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

export interface CreateProtectionRequest {
  domain_id: string;
  layer: ProtectionLayer;
  configuration?: Record<string, unknown>;
}

export interface UpdateProtectionRequest {
  layer?: ProtectionLayer;
  enabled?: boolean;
  status?: ProtectionStatus;
  configuration?: Record<string, unknown>;
}

export interface ProtectionState {
  protection: Protection | null;
  isLoading: boolean;
  error: string | null;
}