import type { Verdict } from "../lib/types";
export function VerdictPill({ verdict }: { verdict: Verdict }) {
  return <span className={`sv-pill sv-pill--${verdict}`}>{verdict}</span>;
}
