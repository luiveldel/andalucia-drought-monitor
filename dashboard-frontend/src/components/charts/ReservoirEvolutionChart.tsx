import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReservoirTimePoint } from "@/types/dashboard-model";
import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function ReservoirEvolutionChart(props: { data: ReservoirTimePoint[] }) {
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

  return (
    <Card className="min-h-[320px]">
      <CardHeader>
        <CardTitle>Regional reservoir fill (monthly)</CardTitle>
        <p className="text-xs text-muted dark:text-muted-dark">Average fill % across monitored basins for the selected range.</p>
      </CardHeader>
      <CardContent className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-black/10 dark:stroke-white/10" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickMargin={6} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={32} unit="%" />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(v) => [`${Number(v).toFixed(1)}%`, "Avg fill"]}
              labelFormatter={(l) => String(l)}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="avg" name="Avg fill %" stroke="#1A6FA3" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
