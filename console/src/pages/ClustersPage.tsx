// P07 — ClustersPage
// Threat-network graph view
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function ClustersPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>Threat-network graph view</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Threat-network clusters</h2><p style={{ color:"var(--sv-text-muted)" }}>Force-directed graph of domains linked by shared ASN / registrar / kit / favicon / JA3.</p></section>
    </AppShell>
  );
}
