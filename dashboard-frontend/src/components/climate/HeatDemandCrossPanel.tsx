import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  HeatDemandCrossProvince,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function Kpi(props: { label: string; value: string; explain: string; tone?: string }) {
  return (
    <div className={cn("rounded-xl border p-3", props.tone ?? "border-border/80")}>
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">{props.explain}</p>
    </div>
  );
}

export function HeatDemandCrossPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const cross = props.autonomy.heat_demand_cross;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: HeatDemandCrossProvince | null | undefined = useMemo(() => {
    if (!cross?.available) return null;
    if (isRegional) return cross.regional;
    return (cross.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [cross, isRegional, props.province]);

  const chart = useMemo(
    () =>
      (cross?.series ?? []).map((d) => ({
        date: d.date.slice(5),
        demand: d.daily_demand_hm3 ?? 0,
        tmax: d.avg_tmax_c ?? null,
        heatProv: d.provinces_in_heat ?? 0,
      })),
    [cross?.series],
  );

  const peaks = useMemo(() => {
    const all = cross?.peak_days ?? [];
    if (isRegional) return all.slice(0, 8);
    return all.filter((p) => p.province_name === props.province).slice(0, 8);
  }, [cross?.peak_days, isRegional, props.province]);

  if (!cross?.available) {
    return (
      <section>
        <SectionHeader
          title="Calor × pico de demanda"
          description={
            cross?.note ||
            "Cruza días muy calurosos con la demanda de riego SiAR para ver cuándo el embalse suele vaciarse más rápido."
          }
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Calor × pico de demanda"
        description={
          cross.definition_es ||
          "Días de estrés térmico cruzados con la demanda de riego SiAR. Un pico es calor + mucha sed del cultivo."
        }
      />
      <Card className="mt-3 border-orange-600/20 dark:border-orange-400/25">
        <CardContent className="space-y-4 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            Miramos los últimos {cross.lookback_days ?? 30} días. Un día cuenta como calor si hay
            estrés térmico en el mart (Tmáx &gt;35 °C y aire seco) o, si falta ese dato, si SiAR marca
            lo mismo. La demanda es la de riego (Kc × ET0 − Pe × ha). Cuando ambos coinciden, el
            vaciado del embalse suele acelerarse.
            {cross.as_of_heat ? ` · calor hasta ${cross.as_of_heat}` : ""}
            {cross.as_of_siar ? ` · SiAR hasta ${cross.as_of_siar}` : ""}.
          </p>

          {!row ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin cruce para {props.province} en la ventana.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <Kpi
                label="Días de calor"
                value={`${row.heat_days ?? 0} / ${row.days_total ?? "—"}`}
                explain="Cuántos días de la ventana fueron térmicamente duros para el cultivo en este ámbito."
                tone="border-orange-600/30 bg-orange-500/5"
              />
              <Kpi
                label="Picos calor+demanda"
                value={String(row.peak_days_count ?? 0)}
                explain="Días calurosos en los que la demanda de riego estuvo en el tercio alto: doble presión sobre el embalse."
                tone="border-rose-600/30 bg-rose-500/5"
              />
              <Kpi
                label="Demanda en calor"
                value={fmt(row.avg_demand_heat_hm3, " hm³/d", 2)}
                explain="Demanda media de riego solo en los días calurosos. Compárala con la de días normales."
              />
              <Kpi
                label="Demanda resto"
                value={fmt(row.avg_demand_other_hm3, " hm³/d", 2)}
                explain="Demanda media en días sin estrés térmico. Si es claramente menor, el calor está empujando el pico."
              />
              <Kpi
                label="Extra por calor"
                value={
                  row.demand_lift_pct != null
                    ? `${row.demand_lift_pct > 0 ? "+" : ""}${fmt(row.demand_lift_pct, " %", 0)}`
                    : "—"
                }
                explain="Cuánto más (o menos) pide el riego en días de calor frente al resto. Positivo = el calor dispara la demanda."
                tone="border-orange-600/30 bg-orange-500/5"
              />
            </div>
          )}

          {chart.length > 1 ? (
            <div>
              <p className="mb-2 text-xs text-muted dark:text-muted-dark">
                Andalucía: barras = demanda de riego total; línea = Tmáx media; el número de provincias
                en calor aparece en el tooltip.
              </p>
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11 }} width={40} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} width={36} />
                    <Tooltip />
                    <Bar
                      yAxisId="left"
                      dataKey="demand"
                      name="Demanda hm³"
                      fill="#ea580c"
                      opacity={0.55}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="tmax"
                      name="Tmáx °C"
                      stroke="#b91c1c"
                      strokeWidth={1.5}
                      dot={false}
                      connectNulls
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {peaks.length > 0 ? (
            <div className="overflow-x-auto">
              <p className="mb-2 text-xs font-medium text-muted dark:text-muted-dark">
                Días pico (calor + demanda alta): conviene mirarlos junto a autonomía y burn rate
              </p>
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">Fecha</th>
                    <th className="pb-2 font-medium">Provincia</th>
                    <th className="pb-2 font-medium">Tmáx</th>
                    <th className="pb-2 font-medium">Demanda</th>
                    <th className="pb-2 font-medium">ET0</th>
                    <th className="pb-2 font-medium">Índice pico</th>
                  </tr>
                </thead>
                <tbody>
                  {peaks.map((p) => (
                    <tr
                      key={`${p.date}-${p.province_name}`}
                      className="border-t border-black/5 dark:border-white/5"
                    >
                      <td className="py-2 tabular-nums">{p.date}</td>
                      <td className="py-2 font-medium">{p.province_name}</td>
                      <td className="py-2 tabular-nums">{fmt(p.tmax_c, " °C", 1)}</td>
                      <td className="py-2 tabular-nums">{fmt(p.daily_demand_hm3, " hm³", 2)}</td>
                      <td className="py-2 tabular-nums">{fmt(p.et0_mm, " mm", 1)}</td>
                      <td className="py-2 tabular-nums font-semibold">{fmt(p.peak_index, "", 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted dark:text-muted-dark">
              En esta ventana no hay días que cumplan a la vez calor fuerte y demanda alta (o aún
              falta historial de solape).
            </p>
          )}

          {(cross.by_province?.length ?? 0) > 0 ? (
            <div className="overflow-x-auto">
              <p className="mb-2 text-xs font-medium text-muted dark:text-muted-dark">
                Por provincia: dónde el calor más empuja la demanda
              </p>
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">Provincia</th>
                    <th className="pb-2 font-medium">Días calor</th>
                    <th className="pb-2 font-medium">Picos</th>
                    <th className="pb-2 font-medium">Extra %</th>
                    <th className="pb-2 font-medium">Dem. calor</th>
                  </tr>
                </thead>
                <tbody>
                  {(cross.by_province ?? []).map((p) => (
                    <tr
                      key={p.province_name}
                      className={cn(
                        "border-t border-black/5 dark:border-white/5",
                        p.province_name === props.province && !isRegional
                          ? "bg-orange-500/5"
                          : "",
                      )}
                    >
                      <td className="py-2 font-medium">{p.province_name}</td>
                      <td className="py-2 tabular-nums">
                        {p.heat_days}/{p.days_total}
                      </td>
                      <td className="py-2 tabular-nums">{p.peak_days_count}</td>
                      <td className="py-2 tabular-nums">
                        {p.demand_lift_pct != null
                          ? `${p.demand_lift_pct > 0 ? "+" : ""}${fmt(p.demand_lift_pct, "%", 0)}`
                          : "—"}
                      </td>
                      <td className="py-2 tabular-nums">{fmt(p.avg_demand_heat_hm3, "", 2)}</td>
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
