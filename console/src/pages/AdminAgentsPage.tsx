// P15 — AdminAgentsPage
// Agent registry + kill-switch + governance budgets
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function AdminAgentsPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>Agent registry + kill-switch + governance budgets</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Agents</h2><button style={{ background:"var(--sv-phish)", color:"#fff", border:"none", borderRadius:"var(--sv-r-sm)", padding:"8px 14px", fontWeight:700 }}>⨯ Global kill-switch</button></section>
    </AppShell>
  );
}
