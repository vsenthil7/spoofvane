// P21 — Forbidden
// 403
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function Forbidden() {
  return <div style={{ display:"grid", placeItems:"center", minHeight:"100vh", background:"var(--sv-bg)", color:"var(--sv-text-muted)", fontFamily:"var(--sv-font-display)" }}><div style={{textAlign:"center"}}><div style={{fontSize:"var(--sv-fs-2xl)", color:"var(--sv-phish)"}}>403</div><p>Your role does not permit access to this surface.</p></div></div>;
}
