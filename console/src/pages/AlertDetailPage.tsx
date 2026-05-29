// P06 — AlertDetailPage
// 10 evidence tabs: Summary, Evidence, Multi-region, Verdict trace, MITRE, Kit, Cluster, Deepfake, Takedown, Audit
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function AlertDetailPage() {
  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>10 evidence tabs</h1>
      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}><h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>Alert detail</h2><div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>{["Summary","Evidence","Multi-region","Verdict trace","MITRE","Kit","Cluster","Deepfake","Takedown","Audit"].map(t=>(<span key={t} style={{ padding:"4px 10px", background:"var(--sv-surface-2)", borderRadius:"var(--sv-r-pill)", fontSize:"var(--sv-fs-xs)", color:"var(--sv-text-muted)" }}>{t}</span>))}</div></section>
    </AppShell>
  );
}
