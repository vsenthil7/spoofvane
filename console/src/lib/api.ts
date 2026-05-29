// Thin typed API client for the SpoofVane backend (FastAPI). Single place that
// knows endpoint shapes; pages call these, never fetch() directly.
//
// v06 §C — Offline seed lane: every call goes through `withSeed()`, which on a
// network error (or when VITE_DEMO=seed) returns the deterministic seed for
// that method and records the data source. AppShell's Demo Health pill reads
// `getLastSource()` to show LIVE (green) vs SEED (amber).
import type { Alert, Brand, AuditRow, CostRow, Verdict } from "./types";
import { SEED } from "./seed";

const BASE = import.meta.env?.VITE_API_BASE ?? "/api";
const FORCE_SEED = import.meta.env?.VITE_DEMO === "seed";

export type DataSource = "live" | "seed";
let _lastSource: DataSource = "live";
const _listeners = new Set<(s: DataSource) => void>();

export function getLastSource(): DataSource {
  return _lastSource;
}
export function onSourceChange(fn: (s: DataSource) => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}
function setSource(s: DataSource) {
  if (s !== _lastSource) {
    _lastSource = s;
    _listeners.forEach(fn => fn(s));
  }
}

async function rawGet<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}
async function rawPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST", credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}

/** Wrap a live fetch: on failure (or forced seed mode) return seed + tag source. */
async function withSeed<T>(method: string, live: () => Promise<T>): Promise<T> {
  if (FORCE_SEED) {
    setSource("seed");
    return SEED[method] as T;
  }
  try {
    const data = await live();
    setSource("live");
    return data;
  } catch {
    setSource("seed");
    if (!(method in SEED)) throw new Error(`no seed for ${method}`);
    return SEED[method] as T;
  }
}

export const api = {
  listBrands: () => withSeed("listBrands", () => rawGet<Brand[]>("/brands")),
  getBrand: (id: string) => withSeed("getBrand", () => rawGet<Brand>(`/brands/${id}`)),
  triageQueue: () => withSeed("triageQueue", () => rawGet<Alert[]>("/alerts?status=triage")),
  getAlert: (id: string) => withSeed("getAlert", () => rawGet<Alert>(`/alerts/${id}`)),
  clusters: () => withSeed("clusters", () => rawGet<{ id: number; members: string[]; risk: number }[]>("/clusters")),
  deepfakes: () => withSeed("deepfakes", () => rawGet<Alert[]>("/deepfakes")),
  audit: (q?: string) => withSeed("audit", () => rawGet<AuditRow[]>(`/audit${q ? `?q=${encodeURIComponent(q)}` : ""}`)),
  reviewQueue: () => withSeed("reviewQueue", () => rawGet<Alert[]>("/review")),
  cost: () => withSeed("cost", () => rawGet<CostRow[]>("/cost")),
  costSummary: () => withSeed("costSummary", () => rawGet<{
    rows: CostRow[]; totalUsd: number; envelopeUsd: number;
    pct: number; throttled: boolean;
  }>("/cost/summary")),
  submitVerdict: (id: string, verdict: Verdict) => rawPost(`/alerts/${id}/verdict`, { verdict }),
  killSwitch: (scope: string) => rawPost("/admin/agents/kill", { scope }),
};
