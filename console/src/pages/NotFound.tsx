// P20 — NotFound
// 404
// Consumes canonical tokens (tokens.css); no hard-coded colors.
import { AppShell } from "../components/AppShell";

export function NotFound() {
  return <div style={{ display:"grid", placeItems:"center", minHeight:"100vh", background:"var(--sv-bg)", color:"var(--sv-text-muted)", fontFamily:"var(--sv-font-display)" }}><div style={{textAlign:"center"}}><div style={{fontSize:"var(--sv-fs-2xl)", color:"var(--sv-brand)"}}>404</div><p>This surface does not exist.</p></div></div>;
}
