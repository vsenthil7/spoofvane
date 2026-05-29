// v06 §A — PURE sidebar collapse logic (no JSX, no React) so it is unit-testable
// under plain Node without a browser or build step. `sidebar.tsx` re-exports
// these. The route-aware/responsive heuristic lives here.

export const ROUTE_COLLAPSE_PREFIXES = ["/alerts/", "/triage", "/review"];
export const RESPONSIVE_BREAKPOINT = 1024;
export const RAIL_W_EXPANDED = 232;
export const RAIL_W_COLLAPSED = 64;

/** Should the rail auto-collapse for this route + viewport width? */
export function shouldAutoCollapse(pathname: string, viewportWidth: number): boolean {
  if (viewportWidth < RESPONSIVE_BREAKPOINT) return true;
  return ROUTE_COLLAPSE_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p)
  );
}

/** Derived rail width in px from collapsed state. */
export function railWidth(isCollapsed: boolean): number {
  return isCollapsed ? RAIL_W_COLLAPSED : RAIL_W_EXPANDED;
}
