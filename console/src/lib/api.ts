// Thin typed API client for the SpoofVane backend (FastAPI). Single place that
// knows endpoint shapes; pages call these, never fetch() directly.
import type { Alert, Brand, AuditRow, CostRow, Verdict } from "./types";

const BASE = import.meta.env?.VITE_API_BASE ?? "/api";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST", credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  listBrands: () => get<Brand[]>("/brands"),
  getBrand: (id: string) => get<Brand>(`/brands/${id}`),
  triageQueue: () => get<Alert[]>("/alerts?status=triage"),
  getAlert: (id: string) => get<Alert>(`/alerts/${id}`),
  clusters: () => get<{ id: number; members: string[]; risk: number }[]>("/clusters"),
  deepfakes: () => get<Alert[]>("/deepfakes"),
  audit: (q?: string) => get<AuditRow[]>(`/audit${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  reviewQueue: () => get<Alert[]>("/review"),
  cost: () => get<CostRow[]>("/cost"),
  submitVerdict: (id: string, verdict: Verdict) => post(`/alerts/${id}/verdict`, { verdict }),
  killSwitch: (scope: string) => post("/admin/agents/kill", { scope }),
};
