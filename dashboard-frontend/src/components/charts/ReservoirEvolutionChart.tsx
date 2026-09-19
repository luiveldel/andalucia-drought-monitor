import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/i18n/useT";
import {
  WATER_FILL_BOTTOM,
  WATER_FILL_MID,
  WATER_FILL_TOP,
  WATER_STROKE,
} from "@/lib/water-chart";
import type { ReservoirTimePoint } from "@/types/dashboard-model";
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function ReservoirEvolutionChart(props: { data: ReservoirTimePoint[] }) {
  const t = useT();
  const series = useMemo(() => {
    const byDate = new Map<string, number[]>();
    for (const r of props.data) {
      const arr = byDate.get(r.date) ?? [];
      arr.push(r.percentage);
      byDate.set(r.date, arr);
    }
    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({
        date,
        avg: Math.round((vals.reduce((s, v) => s + v, 0) / vals.length) * 10) / 10,
      }));
  }, [props.data]);

  const gradId = "reservoir-fill-water";

  return (
    <Card className="min-h-[320px]">
      <CardHeader>
        <CardTitle>{t("chart.title")}</CardTitle>
        <p className="text-xs text-muted dark:text-muted-dark">{t("chart.desc")}</p>
      </CardHeader>
      <CardContent className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={WATER_FILL_TOP} />
                <stop offset="50%" stopColor={WATER_FILL_MID} />
                <stop offset="100%" stopColor={WATER_FILL_BOTTOM} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-black/10 dark:stroke-white/10" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickMargin={6} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={32} unit="%" />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(v) => [`${Number(v).toFixed(1)}%`, t("chart.tooltip")]}
              labelFormatter={(l) => String(l)}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Area
              type="monotone"
              dataKey="avg"
              name={t("chart.series")}
              stroke={WATER_STROKE}
              strokeWidth={2}
              fill={`url(#${gradId})`}
              fillOpacity={1}
              dot={{ r: 3, strokeWidth: 1, fill: "#fff" }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
