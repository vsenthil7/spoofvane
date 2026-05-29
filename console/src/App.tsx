// SpoofVane SOC console — app entry + router.
// Routes are derived from the canonical PAGES registry (lib/pages.ts) so the
// router and the page set can never drift from the 21-page spec.
import { PAGES } from "./lib/pages";
import "./tokens/tokens.css";
import { AdminAgentsPage } from "./pages/AdminAgentsPage";
import { AdminDemoHealthPage } from "./pages/AdminDemoHealthPage";
import { AdminTenantsPage } from "./pages/AdminTenantsPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AlertDetailPage } from "./pages/AlertDetailPage";
import { AuditPage } from "./pages/AuditPage";
import { BrandDetailPage } from "./pages/BrandDetailPage";
import { BrandsPage } from "./pages/BrandsPage";
import { ClustersPage } from "./pages/ClustersPage";
import { CompliancePage } from "./pages/CompliancePage";
import { CostPage } from "./pages/CostPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DeepfakesPage } from "./pages/DeepfakesPage";
import { ExecProtectionPage } from "./pages/ExecProtectionPage";
import { Forbidden } from "./pages/Forbidden";
import { LoginPage } from "./pages/LoginPage";
import { NotFound } from "./pages/NotFound";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TakedownPage } from "./pages/TakedownPage";
import { TriageQueuePage } from "./pages/TriageQueuePage";

const COMPONENTS: Record<string, React.ComponentType> = {
  AdminAgentsPage,
  AdminDemoHealthPage,
  AdminTenantsPage,
  AdminUsersPage,
  AlertDetailPage,
  AuditPage,
  BrandDetailPage,
  BrandsPage,
  ClustersPage,
  CompliancePage,
  CostPage,
  DashboardPage,
  DeepfakesPage,
  ExecProtectionPage,
  Forbidden,
  LoginPage,
  NotFound,
  ReviewQueuePage,
  SettingsPage,
  TakedownPage,
  TriageQueuePage
};

export function resolve(route: string): React.ComponentType {
  const page = PAGES.find(p => p.route === route)
    ?? PAGES.find(p => p.route === "*")!;
  return COMPONENTS[page.component];
}

export default function App({ route = "/" }: { route?: string }) {
  const Page = resolve(route);
  return <Page />;
}

export { PAGES, COMPONENTS };
