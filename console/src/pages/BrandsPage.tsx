// P03 — BrandsPage
// Brand list + brand-wizard launcher
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function BrandsPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>Brand list + brand-wizard launcher</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Protected brands</h2><button style={{ background:"var(--sv-brand)", color:"#1a1300", border:"none", borderRadius:"var(--sv-r-sm)", padding:"8px 14px", fontWeight:700 }}>+ New brand (wizard)</button></section>
    </AppShell>
  );
}
