// SpoofVane SOC console — shared domain types (mirror src/common/models.py).
export type Verdict = "phish" | "suspicious" | "benign";
export type Region = "US" | "EU" | "APAC" | "IN";
export type Role = "owner" | "admin" | "analyst" | "reviewer" | "auditor" | "viewer";

export interface Brand {
  id: string; name: string; loginUrl: string; targetCountry: string;
  keywords: string[]; scoreThreshold: number;
}
export interface Alert {
  id: string; brandId: string; url: string; verdict: Verdict;
  composite: number; family?: string; kit?: string; renderedFrom?: string;
  discoveredAt: string; mitreTechniques: string[];
}
export interface AuditRow {
  seq: number; actorRole: Role; tenantId: string; action: string;
  outcome: string; ts: string; hash: string;
}
export interface CostRow { product: string; usd: number; tenantId: string; }
export interface PageMeta {
  id: string; route: string; title: string; component: string;
  minRole: Role; nav: boolean;
}
