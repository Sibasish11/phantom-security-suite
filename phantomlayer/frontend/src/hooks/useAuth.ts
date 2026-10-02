import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getSession,
  login as authenticate,
  logout as clearAuthentication,
  register as createAccount,
  type AuthSession,
} from "../lib/auth";

import type {
  LoginRequest,
  RegisterRequest,
} from "../lib/api";

export interface UseAuthResult {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (
    payload: LoginRequest,
  ) => Promise<AuthSession>;

  register: (
    payload: RegisterRequest,
  ) => Promise<AuthSession>;

  logout: () => void;

  clearError: () => void;
}

export function useAuth(): UseAuthResult {
  const [session, setSession] =
    useState<AuthSession | null>(null);

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  /*
   * Restore the existing browser session
   * when the application starts.
   */
  useEffect(() => {
    const existingSession = getSession();

    setSession(existingSession);
    setIsLoading(false);
  }, []);

  /*
   * LOGIN
   */
  const login = useCallback(
    async (
      payload: LoginRequest,
    ): Promise<AuthSession> => {
      setIsLoading(true);
      setError(null);

      try {
        const authenticatedSession =
          await authenticate(payload);

        setSession(authenticatedSession);

        return authenticatedSession;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to sign in.";

        setError(message);

        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  /*
   * REGISTER
   */
  const register = useCallback(
    async (
      payload: RegisterRequest,
    ): Promise<AuthSession> => {
      setIsLoading(true);
      setError(null);

      try {
        const authenticatedSession =
          await createAccount(payload);

        setSession(authenticatedSession);

        return authenticatedSession;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to create your account.";

        setError(message);

        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  /*
   * LOGOUT
   */
  const logout = useCallback(() => {
    clearAuthentication();

    setSession(null);
    setError(null);
  }, []);

  /*
   * CLEAR ERROR
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    session,
    isAuthenticated: session !== null,
    isLoading,
    error,

    login,
    register,
    logout,

    clearError,
  };
}