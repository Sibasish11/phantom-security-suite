import {
  login as apiLogin,
  register as apiRegister,
  type AuthResponse,
  type LoginRequest,
  type RegisterRequest,
} from "./api";

import {
  clearStoredSession,
  getAccessToken,
  getStoredOrganization,
  getStoredUser,
  isAuthenticated,
  setAccessToken,
  setStoredOrganization,
  setStoredUser,
  type StoredOrganization,
  type StoredUser,
} from "./storage";

export interface AuthSession {
  accessToken: string;
  user: StoredUser;
  organization: StoredOrganization;
}

function buildSession(
  response: AuthResponse,
): AuthSession {
  const user: StoredUser = {
    user_id: response.user.user_id,
    role: response.user.role,
    email: response.user.email,
    full_name: response.user.full_name,
  };

  const organization: StoredOrganization = {
    organization_id: response.user.organization_id,
    organization_name: response.organization_name || "Your organization",
  };

  setAccessToken(response.access_token);

  setStoredUser(user);

  setStoredOrganization(organization);

  return {
    accessToken: response.access_token,
    user,
    organization,
  };
}

/* =========================================================
   LOGIN
========================================================= */

export async function login(
  payload: LoginRequest,
): Promise<AuthSession> {
  const response = await apiLogin(payload);

  return buildSession(response);
}

/* =========================================================
   REGISTER
========================================================= */

export async function register(
  payload: RegisterRequest,
): Promise<AuthSession> {
  const response = await apiRegister(payload);

  return buildSession(response);
}

/* =========================================================
   CURRENT SESSION
========================================================= */

export function getSession():
  | AuthSession
  | null {
  const accessToken = getAccessToken();
  const user = getStoredUser();
  const organization =
    getStoredOrganization();

  if (
    !accessToken ||
    !user ||
    !organization
  ) {
    return null;
  }

  return {
    accessToken,
    user,
    organization,
  };
}

/* =========================================================
   AUTH STATE
========================================================= */

export function checkAuthentication(): boolean {
  return isAuthenticated();
}

/* =========================================================
   LOGOUT
========================================================= */

export function logout(): void {
  clearStoredSession();
}

/* =========================================================
   ROLE HELPERS
========================================================= */

export function isAdmin(): boolean {
  const user = getStoredUser();

  return user?.role === "admin";
}

export function isAnalyst(): boolean {
  const user = getStoredUser();

  return user?.role === "analyst";
}

export function getCurrentRole(): string | null {
  return getStoredUser()?.role ?? null;
}

/* =========================================================
   ORGANIZATION HELPERS
========================================================= */

export function getOrganizationId(): string | null {
  return (
    getStoredOrganization()
      ?.organization_id ?? null
  );
}

export function getOrganizationName(): string | null {
  return (
    getStoredOrganization()
      ?.organization_name ?? null
  );
}

/* =========================================================
   SESSION RESET
========================================================= */

export function resetAuthentication(): void {
  clearStoredSession();
}