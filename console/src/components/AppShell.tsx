import { PAGES } from "../lib/pages";
import type { Role } from "../lib/types";

// The SOC console chrome: left rail nav (from the canonical page registry),
// top bar with tenant + global kill-switch, content slot. Role-gated nav.
const ROLE_RANK: Record<Role, number> = {
  viewer: 0, auditor: 1, reviewer: 2, analyst: 3, admin: 4, owner: 5,
};

export function AppShell({ role, children }: { role: Role; children: React.ReactNode }) {
  const nav = PAGES.filter(p => p.nav && ROLE_RANK[role] >= ROLE_RANK[p.minRole]);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "232px 1fr", minHeight: "100vh", background: "var(--sv-bg)", color: "var(--sv-text)", fontFamily: "var(--sv-font-sans)" }}>
      <aside style={{ borderRight: "1px solid var(--sv-border)", padding: "var(--sv-s5) var(--sv-s3)" }}>
        <div style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", color: "var(--sv-brand)", letterSpacing: ".02em", marginBottom: "var(--sv-s6)" }}>
          ⬡ SpoofVane
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {nav.map(p => (
            <a key={p.id} href={p.route} style={{ color: "var(--sv-text-muted)", textDecoration: "none", padding: "8px 10px", borderRadius: "var(--sv-r-sm)", fontSize: "var(--sv-fs-sm)" }}>
              {p.title}
            </a>
          ))}
        </nav>
      </aside>
      <main style={{ padding: "var(--sv-s6)" }}>{children}</main>
    </div>
  );
}
