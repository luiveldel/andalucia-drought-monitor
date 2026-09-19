import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { chartToneForId } from "@/lib/water-chart";
import type { MonthlyPrecipPoint, TempAnomalyPoint } from "@/types/dashboard-model";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function ym(year: number, month: number) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function MonthlyAnomalyPanel(props: {
  monthlyPrecip: MonthlyPrecipPoint[];
  tempAnomaly: TempAnomalyPoint[];
}) {
  const precipTone = chartToneForId("monthly_precip");
  const heatTone = chartToneForId("temp_anomaly");

  const precip = [...props.monthlyPrecip]
    .sort((a, b) => a.calendar_year - b.calendar_year || a.calendar_month - b.calendar_month)
    .map((r) => ({ label: ym(r.calendar_year, r.calendar_month), value: Number(r.avg_mm) }));

  const anomaly = [...props.tempAnomaly]
    .sort((a, b) => a.calendar_year - b.calendar_year || a.calendar_month - b.calendar_month)
    .map((r) => ({
      label: ym(r.calendar_year, r.calendar_month),
      value: Number(r.anomaly),
      avg: Number(r.avg_temp),
      baseline: Number(r.baseline_temp),
    }));

  const lastP = precip.at(-1);
  const lastT = anomaly.at(-1);

  return (
    <section className="space-y-3">
      <SectionHeader
        title="Anomalía de temperatura / precipitación mensual"
        description="Precipitación media mensual (mm) y anomalía térmica frente a la climatología reciente. Rojo = calor por encima de la media (problema); azul = agua."
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardContent className="space-y-3 pt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
                Precipitación mensual
              </p>
              {lastP ? (
                <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                  {lastP.value.toLocaleString("es-ES", { maximumFractionDigits: 1 })}
                  <span className="ml-1 text-sm font-medium text-muted">mm</span>
                  <span className="ml-2 text-xs font-normal text-muted">{lastP.label}</span>
                </p>
              ) : null}
            </div>
            {precip.length > 0 ? (
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={precip} margin={{ top: 4, right: 4, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10 }} width={36} />
                    <Tooltip
                      formatter={(v: number) => [`${Number(v).toFixed(1)} mm`, "Precipitación"]}
                      labelFormatter={(l) => String(l)}
                    />
                    <Bar dataKey="value" fill={precipTone.stroke} radius={[3, 3, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted dark:text-muted-dark">Sin serie de precipitación mensual.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 pt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
                Anomalía de temperatura
              </p>
              {lastT ? (
                <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                  {lastT.value >= 0 ? "+" : ""}
                  {lastT.value.toLocaleString("es-ES", { maximumFractionDigits: 2 })}
                  <span className="ml-1 text-sm font-medium text-muted">°C</span>
                  <span className="ml-2 text-xs font-normal text-muted">{lastT.label}</span>
                </p>
              ) : null}
            </div>
            {anomaly.length > 0 ? (
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={anomaly} margin={{ top: 4, right: 4, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10 }} width={36} />
                    <Tooltip
                      formatter={(v: number, _n, item) => {
                        const p = item?.payload as { avg?: number; baseline?: number } | undefined;
                        const extra =
                          p?.avg != null && p?.baseline != null
                            ? ` (media ${p.avg.toFixed(1)} vs base ${p.baseline.toFixed(1)})`
                            : "";
                        const n = Number(v);
                        return [`${n >= 0 ? "+" : ""}${n.toFixed(2)} °C${extra}`, "Anomalía"];
                      }}
                      labelFormatter={(l) => String(l)}
                    />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                      {anomaly.map((d) => (
                        <Cell key={d.label} fill={d.value >= 0 ? heatTone.stroke : precipTone.stroke} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted dark:text-muted-dark">Sin serie de anomalía térmica.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
