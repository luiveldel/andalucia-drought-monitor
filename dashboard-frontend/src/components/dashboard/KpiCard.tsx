import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  WATER_FILL_BOTTOM,
  WATER_FILL_MID,
  WATER_FILL_TOP,
  WATER_STROKE,
} from "@/lib/water-chart";
import type { DashboardKpi } from "@/types/dashboard-model";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export function KpiCard(props: { kpi: DashboardKpi }) {
  const { kpi } = props;
  const spark = (kpi.trend ?? []).map((v, i) => ({ i, v }));
  const barTone: Record<string, string> = {
    normal: "bg-sev-normal",
    warning: "bg-sev-alert",
    emergency: "bg-sev-emergency",
    critical: "bg-sev-critical",
  };
  const bar = barTone[kpi.severity ?? "normal"];
  const gradId = `kpi-water-${kpi.id}`;

  return (
    <Card className="overflow-hidden">
      <div className={cn("h-1 w-full", bar)} />
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
            {kpi.label}
          </p>
          {kpi.severity ? <StatusBadge level={kpi.severity} /> : null}
        </div>
        <p className="mt-2 font-display text-3xl font-semibold tabular-nums tracking-tight text-ink dark:text-ink-dark">
          {kpi.unit === "%" || kpi.unit === "of 8" || kpi.unit === ""
            ? kpi.value.toLocaleString("en-GB", { maximumFractionDigits: kpi.unit ? 1 : 2 })
            : kpi.value.toLocaleString("en-GB", { maximumFractionDigits: 0 })}
          {kpi.unit ? (
            <span className="ml-1 text-lg font-medium text-muted dark:text-muted-dark">{kpi.unit}</span>
          ) : null}
        </p>
        {kpi.delta !== undefined ? (
          <p className="mt-1 text-xs tabular-nums text-muted dark:text-muted-dark">
            Δ {kpi.delta > 0 ? "+" : ""}
            {kpi.delta}
            {kpi.unit === "hm³"
              ? " hm³"
              : kpi.unit === "%"
                ? " %"
                : kpi.unit === "mm"
                  ? " mm"
                  : kpi.unit === "of 8"
                    ? ""
                    : ""}
          </p>
        ) : null}
        {spark.length > 1 ? (
          <div className="mt-3 h-10 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={spark} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={WATER_FILL_TOP} />
                    <stop offset="55%" stopColor={WATER_FILL_MID} />
                    <stop offset="100%" stopColor={WATER_FILL_BOTTOM} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={WATER_STROKE}
                  strokeWidth={1.5}
                  fill={`url(#${gradId})`}
                  fillOpacity={1}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
