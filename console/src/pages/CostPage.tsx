// P13 — CostPage
// Per-tenant Bright Data spend + budget alerting
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function CostPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>Per-tenant Bright Data spend + budget alerting</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Bright Data spend</h2><p style={{ color:"var(--sv-text-muted)" }}>Per-tenant spend vs envelope (free / pro / business / enterprise) with budget alerts.</p></section>
    </AppShell>
  );
}
