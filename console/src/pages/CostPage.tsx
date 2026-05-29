// P13 — CostPage
// Per-tenant Bright Data spend + budget alerting, with the v06 §D back-pressure
// kill-switch surfaced (THROTTLED banner at >=80% of the monthly envelope).
// Consumes canonical tokens (tokens.css); renders backend-down via the seed lane.
import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { api } from "../lib/api";

type Summary = {
  rows: { product: string; usd: number; tenantId: string }[];
  totalUsd: number; envelopeUsd: number; pct: number; throttled: boolean;
};

export function CostPage() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => { api.costSummary().then(setS).catch(() => {}); }, []);

  const pct = s ? Math.round(s.pct * 1000) / 10 : 0;
  const near = s ? s.pct >= 0.8 : false;

  return (
    <AppShell role="analyst">
      <h1 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-2xl)", margin: 0, marginBottom: "var(--sv-s5)" }}>
        Bright Data spend &amp; budget envelope
      </h1>

      {s?.throttled && (
        <div data-testid="kill-switch-banner" role="alert" style={{
          background: "var(--sv-phish-bg)", color: "var(--sv-phish)",
          border: "1px solid var(--sv-phish)", borderRadius: "var(--sv-r-md)",
          padding: "var(--sv-s4)", marginBottom: "var(--sv-s4)",
          fontFamily: "var(--sv-font-mono)", fontSize: "var(--sv-fs-sm)",
        }}>
          ⛔ KILL-SWITCH ENGAGED — BD spend throttled at {pct}% of the monthly
          envelope. Further Bright Data calls are paused until reset.
        </div>
      )}

      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)", marginBottom: "var(--sv-s4)" }}>
        <h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>
          Envelope usage
        </h2>
        {s ? (
          <>
            <div data-testid="envelope-pct" style={{ fontSize: "var(--sv-fs-xl)", color: near ? "var(--sv-suspicious)" : "var(--sv-benign)", fontFamily: "var(--sv-font-mono)" }}>
              ${s.totalUsd.toFixed(2)} / ${s.envelopeUsd.toFixed(2)} ({pct}%)
            </div>
            <div style={{ height: 8, background: "var(--sv-surface-2)", borderRadius: "var(--sv-r-pill)", marginTop: "var(--sv-s2)", overflow: "hidden" }}>
              <div style={{ width: `${Math.min(pct, 100)}%`, height: "100%", background: near ? "var(--sv-suspicious)" : "var(--sv-benign)" }} />
            </div>
          </>
        ) : <p style={{ color: "var(--sv-text-muted)" }}>Loading…</p>}
      </section>

      <section style={{ background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-md)", padding: "var(--sv-s5)" }}>
        <h2 style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-lg)", margin: 0, marginBottom: "var(--sv-s3)" }}>
          Per-product breakdown
        </h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--sv-font-mono)", fontSize: "var(--sv-fs-sm)" }}>
          <thead><tr style={{ color: "var(--sv-text-faint)", textAlign: "left" }}><th>Product</th><th>USD</th></tr></thead>
          <tbody>
            {(s?.rows ?? []).map(r => (
              <tr key={r.product} style={{ borderTop: "1px solid var(--sv-border)" }}>
                <td style={{ padding: "6px 0" }}>{r.product}</td>
                <td>${r.usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
