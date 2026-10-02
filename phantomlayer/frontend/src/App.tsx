import { Overview as AdminOverview } from "./pages/admin/Overview";
import { Incidents as AdminIncidents } from "./pages/admin/Incidents";
import { Events as AdminEvents } from "./pages/admin/Events";
import { Protections as AdminProtections } from "./pages/admin/Protections";
import { Domains as AdminDomains } from "./pages/admin/Domains";
import { Agents as AdminAgents } from "./pages/admin/Agents";
import { Organizations as AdminOrganizations } from "./pages/admin/Organizations";
import { Settings as CustomerSettings } from "./pages/customer/Settings";
import { IncidentDetail as CustomerIncidentDetail } from "./pages/customer/IncidentDetail";
import { Incidents as CustomerIncidents } from "./pages/customer/Incidents";
import { Sessions as CustomerSessions } from "./pages/customer/Sessions";
import { Events as CustomerEvents } from "./pages/customer/Events";
import { Agent as CustomerAgent } from "./pages/customer/Agent";
import { Protection as CustomerProtection } from "./pages/customer/Protection";
import { Overview } from "./pages/customer/Overview";
import type { ReactNode } from "react";
import { getSession } from "./lib/auth";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { PublicLayout } from "./layouts/PublicLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { OnboardingLayout } from "./layouts/OnboardingLayout";
import { CustomerLayout } from "./layouts/CustomerLayout";
import { AdminLayout } from "./layouts/AdminLayout";

import { Landing } from "./pages/public/Landing";
import { HowItWorks } from "./pages/public/HowItWorks";
import { Protection } from "./pages/public/Protection";

import { Login } from "./pages/auth/Login";
import { Signup } from "./pages/auth/Signup";

import { OnboardingWelcome as WelcomeComponent } from "./pages/onboarding/Welcome";
import { DomainSetup as DomainComponent } from "./pages/onboarding/Domain";

import { VerifyDomain } from "./pages/onboarding/VerifyDomain";
import { ChooseProtection } from "./pages/onboarding/ChooseProtection";
import { DeployAgent } from "./pages/onboarding/DeployAgent";
import { Activation } from "./pages/onboarding/Activation";

function Placeholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <AuthLayout>
      <section className="route-error">
        <span className="onboarding-eyebrow">
          PHANTOMLAYER
        </span>

        <h1>{title}</h1>

        <p>{description}</p>
        <Link className="ui-primary" to="/dashboard">Return to workspace →</Link>
      </section>
    </AuthLayout>
  );
}

function AuthenticatedRoute({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const session = getSession();
  const location = useLocation();
  if (!session) return <Navigate to="/login" state={{from: location.pathname + location.search}} replace />;
  if (admin && session.user.role !== 'admin') return <Navigate to="/unauthorized" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      {/* =========================
          PUBLIC
         ========================= */}

      <Route element={<PublicLayout />}>
        <Route
          path="/"
          element={<Landing />}
        />

        <Route
          path="/how-it-works"
          element={<HowItWorks />}
        />

        <Route
          path="/protection"
          element={<Protection />}
        />
      </Route>

      {/* =========================
          AUTH
         ========================= */}

      <Route element={<AuthLayout />}>
        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/signup"
          element={<Signup />}
        />
      </Route>

      {/* =========================
          ONBOARDING
         ========================= */}

      <Route element={<AuthenticatedRoute><OnboardingLayout /></AuthenticatedRoute>}>
        <Route
          path="/onboarding"
          element={<WelcomeComponent />}
        />

        <Route
          path="/onboarding/domain"
          element={<DomainComponent />}
        />

        <Route
          path="/onboarding/domain/verify"
          element={<VerifyDomain />}
        />

        <Route
          path="/onboarding/protection"
          element={<ChooseProtection />}
        />

        <Route
          path="/onboarding/agent"
          element={<DeployAgent />}
        />

        <Route
          path="/onboarding/activation"
          element={<Activation />}
        />
      </Route>

      {/* =========================
          CUSTOMER
         ========================= */}

      <Route element={<AuthenticatedRoute><CustomerLayout /></AuthenticatedRoute>}>
        <Route
          path="/dashboard"
          element={
            <Overview/>
          }
        />

        <Route
          path="/dashboard/protection"
          element=
          {<CustomerProtection/>}
        />

        <Route
          path="/dashboard/agent"
          element={ <CustomerAgent/> }
        />

        <Route
          path="/dashboard/events"
          element={ <CustomerEvents/> }
        />

        <Route
          path="/dashboard/sessions"
          element={
            <CustomerSessions/>
          }
        />

        <Route
          path="/dashboard/incidents"
          element={<CustomerIncidents />}
        />

        <Route
          path="/dashboard/incidents/:id"
          element={<CustomerIncidentDetail />}
        />

        <Route
          path="/dashboard/settings"
          element={<CustomerSettings />}
        />
      </Route>

      {/* =========================
          ADMIN
         ========================= */}

      <Route element={<AuthenticatedRoute admin><AdminLayout /></AuthenticatedRoute>}>

        <Route
          path="/admin"
          element={<AdminOverview />}
        />

        <Route
          path="/admin/organizations"
          element={
            <AdminOrganizations/>
          }
        />

        <Route
          path="/admin/agents"
          element={
            <AdminAgents/>
          }
        />

        <Route
          path="/admin/domains"
          element={
            <AdminDomains/>
          }
        />

        <Route
          path="/admin/protections"
          element={
            <AdminProtections/>
          }
        />

        <Route
          path="/admin/events"
          element={
            <AdminEvents/>
          }
        />


        <Route
          path="/admin/incidents"
          element={
            <AdminIncidents/>
          }
        />
      </Route>

      {/* =========================
          ERRORS
         ========================= */}

      <Route
        path="/unauthorized"
        element={
          <Placeholder
            title="Unauthorized"
            description="You do not have permission to access this page."
          />
        }
      />

      <Route
        path="/404"
        element={
          <Placeholder
            title="Page not found"
            description="The page you're looking for doesn't exist."
          />
        }
      />

      <Route
        path="*"
        element={
          <Navigate
            to="/404"
            replace
          />
        }
      />
    </Routes>
  );
}

export { App };