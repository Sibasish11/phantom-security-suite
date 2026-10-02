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

export interface VerifyDomainResponse
  extends Domain {}

export type DomainVerificationStatus =
  | "unverified"
  | "verifying"
  | "verified"
  | "expired"
  | "failed";

export interface DomainState {
  domain: Domain | null;
  status: DomainVerificationStatus;
  error: string | null;
}