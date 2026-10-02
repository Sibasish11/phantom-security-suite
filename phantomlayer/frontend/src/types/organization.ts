export type OrganizationStatus =
  | "active"
  | "suspended"
  | string;

export type OrganizationRole =
  | "admin"
  | "analyst"
  | string;

export interface Organization {
  organization_id: string;
  organization_name: string;
  status?: OrganizationStatus;
}

export interface OrganizationMember {
  id?: string;
  user_id: string;
  organization_id: string;
  role: OrganizationRole;
  email?: string;
  full_name?: string;
}

export interface Domain {
  id: string;
  domain: string;
  verification_record_name: string;
  verification_token: string;
  token_expires_at: string;
  verified: boolean;
  verified_at: string | null;
}

export interface CreateDomainRequest {
  domain: string;
}

export interface DomainVerificationState {
  domain: Domain | null;
  isVerified: boolean;
  isVerifying: boolean;
  error: string | null;
}