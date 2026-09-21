import { KpiCard } from "@/components/dashboard/KpiCard";
import type { DashboardKpi } from "@/types/dashboard-model";

export function KpiGrid(props: { kpis: DashboardKpi[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-7">
      {props.kpis.map((k) => (
        <KpiCard key={k.id} kpi={k} />
      ))}
    </div>
  );
}
