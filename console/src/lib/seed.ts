// v06 §C — Offline seed lane.
//
// Deterministic seed data for every shape a page consumes, so all pages render
// with the backend DOWN ("demo-day-winning"). Values respect the REAL scoring
// thresholds (composite >= brand.scoreThreshold of 0.65 => phish/suspicious) so
// seeds are plausible, not arbitrary. The api.ts wrapper falls back to these on
// network error or when VITE_DEMO=seed, tagging responses source:"seed".
import type { Alert, Brand, AuditRow, CostRow } from "./types";

export const SEED_BRANDS: Brand[] = [
  { id: "brand_acmebank", name: "AcmeBank", loginUrl: "https://acmebank.com/login",
    targetCountry: "US", keywords: ["acmebank", "acme bank"], scoreThreshold: 0.65 },
  { id: "brand_globex", name: "Globex", loginUrl: "https://globex.com/signin",
    targetCountry: "GB", keywords: ["globex"], scoreThreshold: 0.6 },
];

export const SEED_ALERTS: Alert[] = [
  { id: "alert_seed_001", brandId: "brand_acmebank", url: "https://acmebank-secure-login.top/verify",
    verdict: "phish", composite: 0.91, family: "banking", kit: "16Shop",
    renderedFrom: "US", discoveredAt: "2026-05-29T09:10:00Z",
    mitreTechniques: ["T1566.002", "T1598.003"] },
  { id: "alert_seed_002", brandId: "brand_acmebank", url: "https://my-acmebank-login.xyz/",
    verdict: "suspicious", composite: 0.72, family: "banking", kit: "Tycoon-2FA",
    renderedFrom: "US", discoveredAt: "2026-05-29T09:25:00Z",
    mitreTechniques: ["T1566.002"] },
  { id: "alert_seed_003", brandId: "brand_globex", url: "https://globex-portal-update.cc/",
    verdict: "suspicious", composite: 0.68, family: "m365", kit: "EvilProxy",
    renderedFrom: "GB", discoveredAt: "2026-05-29T08:50:00Z",
    mitreTechniques: ["T1566.002", "T1557"] },
  { id: "alert_seed_004", brandId: "brand_globex", url: "https://globex.com/promo",
    verdict: "benign", composite: 0.21, renderedFrom: "GB",
    discoveredAt: "2026-05-29T07:40:00Z", mitreTechniques: [] },
];

export const SEED_DEEPFAKES: Alert[] = [
  { id: "df_seed_001", brandId: "brand_acmebank", url: "https://youtu.be/fake-ceo-clip",
    verdict: "phish", composite: 0.88, family: "deepfake", kit: "voice-clone",
    discoveredAt: "2026-05-29T06:30:00Z", mitreTechniques: ["T1656"] },
];

export const SEED_CLUSTERS = [
  { id: 1, members: ["alert_seed_001", "alert_seed_002"], risk: 0.86 },
  { id: 2, members: ["alert_seed_003"], risk: 0.68 },
];

export const SEED_AUDIT: AuditRow[] = [
  { seq: 1, actorRole: "analyst", tenantId: "demo", action: "alert.triage",
    outcome: "ok", ts: "2026-05-29T09:30:00Z", hash: "a1b2c3d4" },
  { seq: 2, actorRole: "reviewer", tenantId: "demo", action: "takedown.approve",
    outcome: "ok", ts: "2026-05-29T09:35:00Z", hash: "e5f6a7b8" },
];

export const SEED_COST: CostRow[] = [
  { product: "serp", usd: 4.21, tenantId: "demo" },
  { product: "unlocker", usd: 9.84, tenantId: "demo" },
  { product: "scraping_browser", usd: 12.50, tenantId: "demo" },
  { product: "residential", usd: 6.10, tenantId: "demo" },
];

// One registry keyed by api method name, so the wrapper can look up a fallback
// generically. Keeps seed shapes co-located with the method that returns them.
export const SEED: Record<string, unknown> = {
  listBrands: SEED_BRANDS,
  getBrand: SEED_BRANDS[0],
  triageQueue: SEED_ALERTS.filter(a => a.verdict !== "benign"),
  getAlert: SEED_ALERTS[0],
  clusters: SEED_CLUSTERS,
  deepfakes: SEED_DEEPFAKES,
  audit: SEED_AUDIT,
  reviewQueue: SEED_ALERTS.filter(a => a.verdict === "phish"),
  cost: SEED_COST,
};

/** A seeded value is plausible only if alerts above threshold are non-benign. */
export function seedRespectsThresholds(): boolean {
  return SEED_ALERTS.every(a => {
    const brand = SEED_BRANDS.find(b => b.id === a.brandId);
    if (!brand) return false;
    const above = a.composite >= brand.scoreThreshold;
    return above ? a.verdict !== "benign" : a.verdict === "benign";
  });
}
