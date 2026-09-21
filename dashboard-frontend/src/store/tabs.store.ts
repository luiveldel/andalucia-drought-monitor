import { create } from "zustand";

export type DashboardTab =
  | "decision"
  | "overview"
  | "map"
  | "climate"
  | "irrigation"
  | "risk"
  | "compare"
  | "reservoirs";

const COLLAPSE_KEY = "agro-dashboard-nav-collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

interface TabsState {
  tab: DashboardTab;
  collapsed: boolean;
  setTab: (tab: DashboardTab) => void;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
}

export const useTabsStore = create<TabsState>((set, get) => ({
  tab: "overview",
  collapsed: typeof window === "undefined" ? false : readCollapsed(),
  setTab: (tab) => set({ tab }),
  setCollapsed: (collapsed) => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
    set({ collapsed });
  },
  toggleCollapsed: () => {
    const next = !get().collapsed;
    try {
      localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
    } catch {
      /* ignore */
    }
    set({ collapsed: next });
  },
}));
