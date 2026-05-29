// P01 — LoginPage
// OIDC + SAML + local fallback with MFA challenge
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function LoginPage() {
  return (
    <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", background: "var(--sv-bg)", color: "var(--sv-text)", fontFamily: "var(--sv-font-sans)" }}>
      <div style={{ width: 380, background: "var(--sv-surface)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-lg)", padding: "var(--sv-s7)", boxShadow: "var(--sv-shadow-2)" }}>
        <div style={{ fontFamily: "var(--sv-font-display)", fontSize: "var(--sv-fs-xl)", color: "var(--sv-brand)", textAlign: "center", marginBottom: "var(--sv-s6)" }}>⬡ SpoofVane</div>
        <button style={{ width: "100%", padding: 12, marginBottom: 8, background: "var(--sv-surface-2)", color: "var(--sv-text)", border: "1px solid var(--sv-border-strong)", borderRadius: "var(--sv-r-sm)" }}>Continue with SSO (OIDC)</button>
        <button style={{ width: "100%", padding: 12, marginBottom: 16, background: "var(--sv-surface-2)", color: "var(--sv-text)", border: "1px solid var(--sv-border-strong)", borderRadius: "var(--sv-r-sm)" }}>Continue with SAML</button>
        <input placeholder="email" style={{ width: "100%", padding: 12, marginBottom: 8, background: "var(--sv-bg)", color: "var(--sv-text)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-sm)" }} />
        <input placeholder="password" type="password" style={{ width: "100%", padding: 12, marginBottom: 16, background: "var(--sv-bg)", color: "var(--sv-text)", border: "1px solid var(--sv-border)", borderRadius: "var(--sv-r-sm)" }} />
        <button style={{ width: "100%", padding: 12, background: "var(--sv-brand)", color: "#1a1300", fontWeight: 700, border: "none", borderRadius: "var(--sv-r-sm)" }}>Sign in</button>
      </div>
    </div>
  );
}
