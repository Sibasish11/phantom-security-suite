export type UserRole =
  | "admin"
  | "analyst"
  | string;

export interface User {
  user_id: string;
  email?: string;
  full_name?: string;
  role: UserRole;
}

export interface Organization {
  organization_id: string;
  organization_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SignupPayload {
  organization_name: string;
  full_name: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  organization_id: string;
  organization_name: string;
  role: UserRole;
}

export interface AuthSession {
  accessToken: string;
  user: User;
  organization: Organization;
}

export interface AuthState {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}