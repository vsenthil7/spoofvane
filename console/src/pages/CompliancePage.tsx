// P14 — CompliancePage
// SOC 2 / ISO / DORA / NIS2 evidence + status
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function CompliancePage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>SOC 2 / ISO / DORA / NIS2 evidence + status</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Compliance evidence</h2><div style={{ display:"flex", gap:8 }}>{["SOC 2","ISO 27001","DORA","NIS2"].map(f=>(<span key={f} style={{ padding:"4px 10px", background:"var(--sv-benign-bg)", color:"var(--sv-benign)", borderRadius:"var(--sv-r-pill)", fontSize:"var(--sv-fs-xs)" }}>{f}</span>))}</div></section>
    </AppShell>
  );
}
