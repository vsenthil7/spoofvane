// P11 — AuditPage
// NL-searchable hash-chained audit log
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function AuditPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>NL-searchable hash-chained audit log</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Audit log</h2><input placeholder="Ask: analyst takedown actions for tenant acme" style={{ width:"100%", padding:10, background:"var(--sv-bg)", color:"var(--sv-text)", border:"1px solid var(--sv-border)", borderRadius:"var(--sv-r-sm)" }} /></section>
    </AppShell>
  );
}
