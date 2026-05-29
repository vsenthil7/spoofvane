import { useEffect } from "react";
import { PAGES } from "../lib/pages";
import type { Role } from "../lib/types";
import {
  SidebarProvider,
  useSidebar,
  shouldAutoCollapse,
  railWidth,
} from "../lib/sidebar";

// The SOC console chrome: collapsible left rail nav (from the canonical page
// registry), top bar with tenant + global kill-switch, content slot. Role-gated.
//
// v06 §A — Collapse behaviour:
//   * Explicit: chevron toggle in the brand header, or the "[" keyboard key.
//   * Route-aware: auto-collapses on /alerts/:id, /triage, /review (need room).
//   * Responsive: auto-collapses when viewport < 1024px.
//   * Collapsed mode renders ICONS ONLY; labels are aria-hidden + shown as
//     hover tooltips. Width animates 232px <-> 64px (160ms).
// In-app state only — no localStorage (artifact rule).
const ROLE_RANK: Record<Role, number> = {
  viewer: 0, auditor: 1, reviewer: 2, analyst: 3, admin: 4, owner: 5,
};

function Shell({ role, children }: { role: Role; children: React.ReactNode }) {
  const { isCollapsed, toggle, setCollapsed } = useSidebar();
  const nav = PAGES.filter(p => p.nav && ROLE_RANK[role] >= ROLE_RANK[p.minRole]);

  // Route-aware + responsive auto-collapse. Re-evaluated on route change and
  // on window resize. (Uses the pure heuristic from lib/sidebar.)
  useEffect(() => {
    function evaluate() {
      const path = window.location.pathname;
      const w = window.innerWidth;
      if (shouldAutoCollapse(path, w)) setCollapsed(true);
    }
    evaluate();
    window.addEventListener("resize", evaluate);
    window.addEventListener("popstate", evaluate);
    return () => {
      window.removeEventListener("resize", evaluate);
      window.removeEventListener("popstate", evaluate);
    };
  }, [setCollapsed]);

  const railW = railWidth(isCollapsed);

  return (
    <div
      data-testid="app-shell"
      style={{
        display: "grid",
        gridTemplateColumns: `${railW}px 1fr`,
        transition: "grid-template-columns 160ms ease",
        minHeight: "100vh",
        background: "var(--sv-bg)",
        color: "var(--sv-text)",
        fontFamily: "var(--sv-font-sans)",
      }}
    >
      <aside
        data-testid="sidebar-rail"
        data-collapsed={isCollapsed ? "true" : "false"}
        style={{
          width: railW,
          borderRight: "1px solid var(--sv-border)",
          padding: isCollapsed ? "var(--sv-s5) var(--sv-s2)" : "var(--sv-s5) var(--sv-s3)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: isCollapsed ? "center" : "space-between",
            marginBottom: "var(--sv-s6)",
          }}
        >
          <div
            style={{
              fontFamily: "var(--sv-font-display)",
              fontSize: "var(--sv-fs-lg)",
              color: "var(--sv-brand)",
              letterSpacing: ".02em",
              whiteSpace: "nowrap",
            }}
          >
            {isCollapsed ? "\u2b22" : "\u2b22 SpoofVane"}
          </div>
          <button
            type="button"
            data-testid="sidebar-toggle"
            aria-label="Toggle sidebar"
            onClick={toggle}
            style={{
              background: "transparent",
              border: "1px solid var(--sv-border)",
              borderRadius: "var(--sv-r-sm)",
              color: "var(--sv-text-muted)",
              cursor: "pointer",
              padding: "2px 6px",
              fontSize: "var(--sv-fs-sm)",
              display: isCollapsed ? "none" : "inline-block",
            }}
          >
            {"\u2039"}
          </button>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {nav.map(p => (
            <a
              key={p.id}
              href={p.route}
              title={isCollapsed ? p.title : undefined}
              data-testid={`nav-${p.id}`}
              style={{
                color: "var(--sv-text-muted)",
                textDecoration: "none",
                padding: "8px 10px",
                borderRadius: "var(--sv-r-sm)",
                fontSize: "var(--sv-fs-sm)",
                display: "flex",
                alignItems: "center",
                gap: 10,
                justifyContent: isCollapsed ? "center" : "flex-start",
                whiteSpace: "nowrap",
              }}
            >
              <span aria-hidden="true" style={{ fontSize: "1.05em" }}>{p.icon ?? "\u2022"}</span>
              <span
                data-testid={`nav-label-${p.id}`}
                aria-hidden={isCollapsed ? "true" : undefined}
                style={{ display: isCollapsed ? "none" : "inline" }}
              >
                {p.title}
              </span>
            </a>
          ))}
        </nav>
      </aside>
      <main style={{ padding: "var(--sv-s6)" }}>{children}</main>
    </div>
  );
}

export function AppShell({ role, children }: { role: Role; children: React.ReactNode }) {
  // Seed initial collapse from current route/width so first paint is correct.
  const initialCollapsed =
    typeof window !== "undefined" &&
    shouldAutoCollapse(window.location.pathname, window.innerWidth);
  return (
    <SidebarProvider initialCollapsed={initialCollapsed}>
      <Shell role={role}>{children}</Shell>
    </SidebarProvider>
  );
}
