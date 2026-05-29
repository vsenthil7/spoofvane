// Canonical 21-page registry (review §9 P01–P21). The router, the nav, the
// AdminDemoHealth coverage check, and the Playwright snapshot suite all read
// this single list so "21 pages" is enforced in one place.
import type { PageMeta } from "./types";

export const PAGES: PageMeta[] = [
  { id: "P01", route: "/login",            title: "Sign in",            component: "LoginPage",          minRole: "viewer",   nav: false, icon: "\u2192" },
  { id: "P02", route: "/",                 title: "Dashboard",          component: "DashboardPage",      minRole: "viewer",   nav: true,  icon: "\u25a6" },
  { id: "P03", route: "/brands",           title: "Brands",             component: "BrandsPage",         minRole: "analyst",  nav: true,  icon: "\u25c8" },
  { id: "P04", route: "/brands/:id",       title: "Brand detail",       component: "BrandDetailPage",    minRole: "analyst",  nav: false, icon: "\u25c8" },
  { id: "P05", route: "/triage",           title: "Triage queue",       component: "TriageQueuePage",    minRole: "analyst",  nav: true,  icon: "\u2691" },
  { id: "P06", route: "/alerts/:id",       title: "Alert detail",       component: "AlertDetailPage",    minRole: "analyst",  nav: false, icon: "\u26a0" },
  { id: "P07", route: "/clusters",         title: "Clusters",           component: "ClustersPage",       minRole: "analyst",  nav: true,  icon: "\u2756" },
  { id: "P08", route: "/deepfakes",        title: "Deepfakes",          component: "DeepfakesPage",      minRole: "analyst",  nav: true,  icon: "\u25d0" },
  { id: "P09", route: "/exec-protection",  title: "Exec protection",    component: "ExecProtectionPage", minRole: "analyst",  nav: true,  icon: "\u2605" },
  { id: "P10", route: "/takedowns",        title: "Takedowns",          component: "TakedownPage",       minRole: "analyst",  nav: true,  icon: "\u2702" },
  { id: "P11", route: "/audit",            title: "Audit",              component: "AuditPage",          minRole: "auditor",  nav: true,  icon: "\u26d3" },
  { id: "P12", route: "/review",           title: "Review queue",       component: "ReviewQueuePage",    minRole: "reviewer", nav: true,  icon: "\u2713" },
  { id: "P13", route: "/cost",             title: "Cost",               component: "CostPage",           minRole: "admin",    nav: true,  icon: "\u00a4" },
  { id: "P14", route: "/compliance",       title: "Compliance",         component: "CompliancePage",     minRole: "auditor",  nav: true,  icon: "\u00a7" },
  { id: "P15", route: "/admin/agents",     title: "Agents",             component: "AdminAgentsPage",    minRole: "admin",    nav: true,  icon: "\u26ed" },
  { id: "P16", route: "/admin/users",      title: "Users",              component: "AdminUsersPage",     minRole: "admin",    nav: true,  icon: "\u2637" },
  { id: "P17", route: "/admin/tenants",    title: "Tenants",            component: "AdminTenantsPage",   minRole: "owner",    nav: true,  icon: "\u2302" },
  { id: "P18", route: "/admin/demo-health",title: "Demo health",        component: "AdminDemoHealthPage",minRole: "admin",    nav: true,  icon: "\u2665" },
  { id: "P19", route: "/settings",         title: "Settings",           component: "SettingsPage",       minRole: "viewer",   nav: true,  icon: "\u2699" },
  { id: "P20", route: "*",                 title: "Not found",          component: "NotFound",           minRole: "viewer",   nav: false, icon: "\u2717" },
  { id: "P21", route: "/403",              title: "Forbidden",          component: "Forbidden",          minRole: "viewer",   nav: false, icon: "\u26d4" },
];

export const PAGE_COUNT = PAGES.length; // must equal 21
