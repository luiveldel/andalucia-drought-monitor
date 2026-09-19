import { create } from "zustand";
import type { DashboardTimeRange } from "@/types/dashboard-model";

interface DashboardFiltersState {
  timeRange: DashboardTimeRange;
  selectedProvince: string | null;
  selectedSeverity: string | null;
  setTimeRange: (r: DashboardTimeRange) => void;
  setSelectedProvince: (p: string | null) => void;
  setSelectedSeverity: (s: string | null) => void;
}

export const useDashboardFilters = create<DashboardFiltersState>((set) => ({
  timeRange: "12m",
  selectedProvince: null,
  selectedSeverity: null,
  setTimeRange: (timeRange) => set({ timeRange }),
  setSelectedProvince: (selectedProvince) => set({ selectedProvince }),
  setSelectedSeverity: (selectedSeverity) => set({ selectedSeverity }),
}));
