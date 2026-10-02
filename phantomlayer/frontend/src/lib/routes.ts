export const routes = {
  public: {
    home: "/",
    howItWorks: "/how-it-works",
    protection: "/protection",
  },

  auth: {
    login: "/login",
    signup: "/signup",
  },

  onboarding: {
    welcome: "/onboarding",
    domain: "/onboarding/domain",
    verifyDomain: "/onboarding/domain/verify",
    chooseProtection: "/onboarding/protection",
    deployAgent: "/onboarding/agent",
    activation: "/onboarding/activation",
  },

  customer: {
    overview: "/dashboard",
    protection: "/dashboard/protection",
    agent: "/dashboard/agent",
    events: "/dashboard/events",
    sessions: "/dashboard/sessions",
    incidents: "/dashboard/incidents",
    incidentDetail: (
      incidentId: string,
    ) =>
      `/dashboard/incidents/${incidentId}`,
    settings: "/dashboard/settings",
  },

  admin: {
    overview: "/admin",
    organizations: "/admin/organizations",
    agents: "/admin/agents",
    domains: "/admin/domains",
    protections: "/admin/protections",
    events: "/admin/events",
    incidents: "/admin/incidents",
  },

  errors: {
    unauthorized: "/unauthorized",
    notFound: "/404",
  },
} as const;

/* =========================================================
   Route helpers
========================================================= */

export function isPublicRoute(
  pathname: string,
): boolean {
  return (
    pathname === routes.public.home ||
    pathname === routes.public.howItWorks ||
    pathname === routes.public.protection
  );
}

export function isAuthRoute(
  pathname: string,
): boolean {
  return (
    pathname === routes.auth.login ||
    pathname === routes.auth.signup
  );
}

export function isOnboardingRoute(
  pathname: string,
): boolean {
  return pathname.startsWith(
    "/onboarding",
  );
}

export function isCustomerRoute(
  pathname: string,
): boolean {
  return pathname.startsWith(
    "/dashboard",
  );
}

export function isAdminRoute(
  pathname: string,
): boolean {
  return pathname === "/admin" ||
    pathname.startsWith("/admin/");
}

/* =========================================================
   Navigation helpers
========================================================= */

export function getIncidentRoute(
  incidentId: string,
): string {
  return routes.customer.incidentDetail(
    incidentId,
  );
}

export function getDefaultRoute(
  role?: string | null,
): string {
  if (role === "admin") {
    return routes.customer.overview;
  }

  if (role === "analyst") {
    return routes.customer.overview;
  }

  return routes.public.home;
}   