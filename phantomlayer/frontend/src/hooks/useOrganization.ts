import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  createDomain,
  createProtection,
  getAgents,
  getDomains,
  getProtections,
  type Agent,
  type Domain,
  type Protection,
  type ProtectionLayer,
} from "../lib/api";

import {
  getSession,
} from "../lib/auth";

export interface OrganizationState {
  domains: Domain[];
  protections: Protection[];
  agents: Agent[];

  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
}

export interface UseOrganizationResult
  extends OrganizationState {
  refresh: () => Promise<void>;

  addDomain: (
    domain: string,
  ) => Promise<Domain>;

  addProtection: (
    domainId: string,
    layer: ProtectionLayer,
    configuration?: Record<string, unknown>,
  ) => Promise<Protection>;

  verifiedDomain: Domain | null;

  activeProtection: Protection | null;

  connectedAgent: Agent | null;
}

export function useOrganization(): UseOrganizationResult {
  const [domains, setDomains] = useState<
    Domain[]
  >([]);

  const [protections, setProtections] =
    useState<Protection[]>([]);

  const [agents, setAgents] = useState<
    Agent[]
  >([]);

  const [isLoading, setIsLoading] =
    useState(true);

  const [isRefreshing, setIsRefreshing] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  /*
   * Load all organization-level resources.
   *
   * These endpoints are already tenant-aware
   * on the PhantomLayer backend, so the frontend
   * does not need to send organization_id manually.
   */
  const refresh = useCallback(
    async () => {
      const session = getSession();

      if (!session) {
        setDomains([]);
        setProtections([]);
        setAgents([]);
        setIsLoading(false);

        return;
      }

      setError(null);
      setIsRefreshing(true);

      try {
        const [
          domainResponse,
          protectionResponse,
          agentResponse,
        ] = await Promise.all([
          getDomains(),
          getProtections(),
          getAgents(),
        ]);

        setDomains(domainResponse);
        setProtections(protectionResponse);
        setAgents(agentResponse);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to load organization data.";

        setError(message);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [],
  );

  /*
   * Load organization data when the hook
   * first mounts.
   */
  useEffect(() => {
    void refresh();
  }, [refresh]);

  /*
   * CREATE DOMAIN
   */
  const addDomain = useCallback(
    async (
      domain: string,
    ): Promise<Domain> => {
      setError(null);

      try {
        const created =
          await createDomain(domain);

        setDomains((current) => [
          ...current,
          created,
        ]);

        return created;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to add domain.";

        setError(message);

        throw err;
      }
    },
    [],
  );

  /*
   * CREATE PROTECTION
   */
  const addProtection = useCallback(
    async (
      domainId: string,
      layer: ProtectionLayer,
      configuration: Record<string, unknown> = {},
    ): Promise<Protection> => {
      setError(null);

      try {
        const created =
          await createProtection({
            domain_id: domainId,
            layer,
            configuration,
          });

        setProtections((current) => [
          ...current,
          created,
        ]);

        return created;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to create protection.";

        setError(message);

        throw err;
      }
    },
    [],
  );

  /*
   * Find the first verified domain.
   */
  const verifiedDomain =
    domains.find(
      (domain) => domain.verified,
    ) ?? null;

  /*
   * Find an active protection.
   */
  const activeProtection =
    protections.find(
      (protection) =>
        protection.enabled &&
        protection.status === "active",
    ) ?? null;

  /*
   * Find the agent that is currently
   * connected to PhantomLayer.
   *
   * Healthy is the real active state.
   * Degraded is still connected but unhealthy.
   */
  const connectedAgent =
    agents.find(
      (agent) =>
        agent.status === "healthy" ||
        agent.status === "degraded",
    ) ?? null;

  return {
    domains,
    protections,
    agents,

    isLoading,
    isRefreshing,
    error,

    refresh,
    addDomain,
    addProtection,

    verifiedDomain,
    activeProtection,
    connectedAgent,
  };
}