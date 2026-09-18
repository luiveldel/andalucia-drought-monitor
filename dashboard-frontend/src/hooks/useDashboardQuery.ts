import { useQuery } from "@tanstack/react-query";
import { fetchDashboardSnapshot } from "@/services/dashboard/dashboard.service";
import { useDashboardFilters } from "@/store/filters.store";

export function useDashboardQuery() {
  const timeRange = useDashboardFilters((s) => s.timeRange);
  return useQuery({
    queryKey: ["dashboard", timeRange],
    queryFn: () => fetchDashboardSnapshot(timeRange),
  });
}
