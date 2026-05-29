// v06 §A — Sidebar collapse state + route-aware / responsive heuristic.
//
// In-app state only (no localStorage — artifact rule). The collapse heuristic
// is extracted into a PURE function `shouldAutoCollapse()` so it can be unit
// tested without a browser (the Playwright pixel assertion is BLOCKED-ENV in
// the sandbox; this logic test is not).
//
// Heuristic (documented per v06 §A.6):
//   - Auto-collapse on detail/queue routes that need horizontal room:
//     /alerts/:id, /triage, /review.
//   - Auto-collapse when viewport width < 1024 (responsive).
//   - Otherwise leave the user's explicit choice alone.
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  shouldAutoCollapse,
  railWidth,
  ROUTE_COLLAPSE_PREFIXES,
  RESPONSIVE_BREAKPOINT,
  RAIL_W_EXPANDED,
  RAIL_W_COLLAPSED,
} from "./sidebar-logic";

export {
  shouldAutoCollapse,
  railWidth,
  ROUTE_COLLAPSE_PREFIXES,
  RESPONSIVE_BREAKPOINT,
  RAIL_W_EXPANDED,
  RAIL_W_COLLAPSED,
};

interface SidebarState {
  isCollapsed: boolean;
  toggle: () => void;
  setCollapsed: (v: boolean) => void;
}

const SidebarContext = createContext<SidebarState | null>(null);

export function SidebarProvider({
  children,
  initialCollapsed = false,
}: {
  children: React.ReactNode;
  initialCollapsed?: boolean;
}) {
  const [isCollapsed, setCollapsed] = useState(initialCollapsed);
  const toggle = () => setCollapsed((v) => !v);

  // Keyboard toggle: "[" flips state, ignored while typing in a field.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "[") return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || el?.isContentEditable) return;
      setCollapsed((v) => !v);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo(
    () => ({ isCollapsed, toggle, setCollapsed }),
    [isCollapsed]
  );
  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
}

export function useSidebar(): SidebarState {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar must be used within <SidebarProvider>");
  return ctx;
}
