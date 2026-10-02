const ACCESS_TOKEN_KEY = "phantomlayer_access_token";
const USER_KEY = "phantomlayer_user";
const ORGANIZATION_KEY = "phantomlayer_organization";

export interface StoredUser {
  user_id: string;
  email?: string;
  full_name?: string;
  role: string;
}

export interface StoredOrganization {
  organization_id: string;
  organization_name: string;
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(
  token: string,
): void {
  localStorage.setItem(
    ACCESS_TOKEN_KEY,
    token,
  );
}

export function removeAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getStoredUser(): StoredUser | null {
  const value = localStorage.getItem(USER_KEY);

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as StoredUser;
  } catch {
    removeStoredUser();
    return null;
  }
}

export function setStoredUser(
  user: StoredUser,
): void {
  localStorage.setItem(
    USER_KEY,
    JSON.stringify(user),
  );
}

export function removeStoredUser(): void {
  localStorage.removeItem(USER_KEY);
}

export function getStoredOrganization():
  | StoredOrganization
  | null {
  const value = localStorage.getItem(
    ORGANIZATION_KEY,
  );

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as StoredOrganization;
  } catch {
    removeStoredOrganization();
    return null;
  }
}

export function setStoredOrganization(
  organization: StoredOrganization,
): void {
  localStorage.setItem(
    ORGANIZATION_KEY,
    JSON.stringify(organization),
  );
}

export function removeStoredOrganization(): void {
  localStorage.removeItem(
    ORGANIZATION_KEY,
  );
}

export function clearStoredSession(): void {
  removeAccessToken();
  removeStoredUser();
  removeStoredOrganization();
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}