// P02 — DashboardPage
// SOC overview — KPI tiles, family pie, region map, live pipeline strip
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function DashboardPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>SOC overview</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Threat posture</h2><div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"var(--sv-s4)" }}>{["Active alerts","Phish today","Takedowns open","BD spend (mo)"].map(k=>(<div key={k} style={{ background:"var(--sv-surface-2)", borderRadius:"var(--sv-r-sm)", padding:"var(--sv-s4)" }}><div style={{ color:"var(--sv-text-faint)", fontSize:"var(--sv-fs-xs)" }}>{k}</div><div style={{ fontFamily:"var(--sv-font-mono)", fontSize:"var(--sv-fs-xl)", color:"var(--sv-brand)" }}>—</div></div>))}</div></section>
    </AppShell>
  );
}
