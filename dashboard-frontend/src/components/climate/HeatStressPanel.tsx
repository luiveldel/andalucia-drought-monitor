import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { chartToneForId } from "@/lib/water-chart";
import type { HeatStressSnapshot } from "@/types/dashboard-model";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function HeatStressPanel(props: { heatStress: HeatStressSnapshot }) {
  const hs = props.heatStress;
  const tone = chartToneForId("heat");
  const series = (hs.recent_days ?? []).map((d) => ({
    date: d.observation_date,
    risk: Number(d.agricultural_risk_index),
    stations: Number(d.stations_in_heat_stress),
    provinces: Number(d.provinces_affected),
    temp: Number(d.avg_max_temp_c),
  }));
  const top = (hs.latest ?? []).slice(0, 8);

  return (
    <section className="space-y-3">
      <SectionHeader
        title="Estrés térmico"
        description="Días con Tmáx > 35 °C y humedad mínima < 30 %. El índice agrícola combina calor con bajo llenado de embalses."
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                Último día con estrés
              </p>
              <p className="font-display text-2xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                {hs.as_of ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                Provincias (último día)
              </p>
              <p className="font-display text-2xl font-semibold tabular-nums">{top.length}</p>
            </div>
          </div>

          {!hs.available ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin datos de estrés térmico. Ejecuta{" "}
              <code className="text-xs">dbt run --select fact_heat_stress_days</code>.
            </p>
          ) : null}

          {series.length > 1 ? (
            <div className="h-28 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="heat-risk-fill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={tone.fillTop} />
                      <stop offset="55%" stopColor={tone.fillMid} />
                      <stop offset="100%" stopColor={tone.fillBottom} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10 }} width={36} />
                  <Tooltip
                    formatter={(v: number, name: string) => {
                      if (name === "risk") return [Number(v).toFixed(2), "Índice riesgo"];
                      return [v, name];
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="risk"
                    stroke={tone.stroke}
                    fill="url(#heat-risk-fill)"
                    strokeWidth={1.5}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : null}

          {top.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">Provincia</th>
                    <th className="pb-2 font-medium">Estaciones</th>
                    <th className="pb-2 font-medium">Tmáx media</th>
                    <th className="pb-2 font-medium">Llenado</th>
                    <th className="pb-2 font-medium">Índice riesgo</th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((r) => (
                    <tr
                      key={`${r.province_name}-${r.observation_date}`}
                      className="border-t border-black/5 dark:border-white/5"
                    >
                      <td className="py-2 font-medium">{r.province_name}</td>
                      <td className="py-2 tabular-nums">{r.stations_in_heat_stress}</td>
                      <td className="py-2 tabular-nums">{r.avg_max_temp_c.toFixed(1)} °C</td>
                      <td className="py-2 tabular-nums">
                        {r.reservoir_fill_pct != null ? `${r.reservoir_fill_pct.toFixed(1)} %` : "—"}
                      </td>
                      <td
                        className={cn(
                          "py-2 tabular-nums font-semibold",
                          r.agricultural_risk_index >= 20
                            ? "text-sev-critical"
                            : r.agricultural_risk_index >= 12
                              ? "text-sev-emergency"
                              : "text-ink dark:text-ink-dark",
                        )}
                      >
                        {r.agricultural_risk_index.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
