// Canonical 21-page registry (review §9 P01–P21). The router, the nav, the
// AdminDemoHealth coverage check, and the Playwright snapshot suite all read
// this single list so "21 pages" is enforced in one place.
import type { PageMeta } from "./types";

export const PAGES: PageMeta[] = [
  { id: "P01", route: "/login",            title: "Sign in",            component: "LoginPage",          minRole: "viewer",   nav: false },
  { id: "P02", route: "/",                 title: "Dashboard",          component: "DashboardPage",      minRole: "viewer",   nav: true  },
  { id: "P03", route: "/brands",           title: "Brands",             component: "BrandsPage",         minRole: "analyst",  nav: true  },
  { id: "P04", route: "/brands/:id",       title: "Brand detail",       component: "BrandDetailPage",    minRole: "analyst",  nav: false },
  { id: "P05", route: "/triage",           title: "Triage queue",       component: "TriageQueuePage",    minRole: "analyst",  nav: true  },
  { id: "P06", route: "/alerts/:id",       title: "Alert detail",       component: "AlertDetailPage",    minRole: "analyst",  nav: false },
  { id: "P07", route: "/clusters",         title: "Clusters",           component: "ClustersPage",       minRole: "analyst",  nav: true  },
  { id: "P08", route: "/deepfakes",        title: "Deepfakes",          component: "DeepfakesPage",      minRole: "analyst",  nav: true  },
  { id: "P09", route: "/exec-protection",  title: "Exec protection",    component: "ExecProtectionPage", minRole: "analyst",  nav: true  },
  { id: "P10", route: "/takedowns",        title: "Takedowns",          component: "TakedownPage",       minRole: "analyst",  nav: true  },
  { id: "P11", route: "/audit",            title: "Audit",              component: "AuditPage",          minRole: "auditor",  nav: true  },
  { id: "P12", route: "/review",           title: "Review queue",       component: "ReviewQueuePage",    minRole: "reviewer", nav: true  },
  { id: "P13", route: "/cost",             title: "Cost",               component: "CostPage",           minRole: "admin",    nav: true  },
  { id: "P14", route: "/compliance",       title: "Compliance",         component: "CompliancePage",     minRole: "auditor",  nav: true  },
  { id: "P15", route: "/admin/agents",     title: "Agents",             component: "AdminAgentsPage",    minRole: "admin",    nav: true  },
  { id: "P16", route: "/admin/users",      title: "Users",              component: "AdminUsersPage",     minRole: "admin",    nav: true  },
  { id: "P17", route: "/admin/tenants",    title: "Tenants",            component: "AdminTenantsPage",   minRole: "owner",    nav: true  },
  { id: "P18", route: "/admin/demo-health",title: "Demo health",        component: "AdminDemoHealthPage",minRole: "admin",    nav: true  },
  { id: "P19", route: "/settings",         title: "Settings",           component: "SettingsPage",       minRole: "viewer",   nav: true  },
  { id: "P20", route: "*",                 title: "Not found",          component: "NotFound",           minRole: "viewer",   nav: false },
  { id: "P21", route: "/403",              title: "Forbidden",          component: "Forbidden",          minRole: "viewer",   nav: false },
];

export const PAGE_COUNT = PAGES.length; // must equal 21
