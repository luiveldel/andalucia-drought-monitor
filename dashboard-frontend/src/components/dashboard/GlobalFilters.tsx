import { Button } from "@/components/ui/button";
import { useT } from "@/i18n/useT";
import { useDashboardFilters } from "@/store/filters.store";
import type { DashboardTimeRange } from "@/types/dashboard-model";

const RANGES: { id: DashboardTimeRange; label: string }[] = [
  { id: "30d", label: "30d" },
  { id: "90d", label: "90d" },
  { id: "12m", label: "12m" },
];

export function GlobalFilters() {
  const t = useT();
  const timeRange = useDashboardFilters((s) => s.timeRange);
  const setTimeRange = useDashboardFilters((s) => s.setTimeRange);
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label={t("filters.aria")}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
        {t("filters.range")}
      </span>
      {RANGES.map((r) => (
        <Button
          key={r.id}
          className={
            timeRange === r.id
              ? "border-water bg-water/10 text-water dark:border-water dark:bg-water/15 dark:text-water"
              : ""
          }
          onClick={() => setTimeRange(r.id)}
        >
          {r.label}
        </Button>
      ))}
    </div>
  );
}
