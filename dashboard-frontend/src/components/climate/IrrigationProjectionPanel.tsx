import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  IrrigationAutonomySnapshot,
  IrrigationProjectionProvince,
} from "@/types/dashboard-model";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

export function IrrigationProjectionPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const proj = props.autonomy.projection;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: IrrigationProjectionProvince | null | undefined = useMemo(() => {
    if (!proj?.available) return null;
    if (isRegional) return proj.regional;
    return (proj.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [isRegional, proj, props.province]);

  const chart = useMemo(
    () =>
      (row?.days ?? []).map((d) => ({
        date: d.date.slice(5),
        days: d.days_autonomy ?? 0,
        stored: d.stored_hm3 ?? 0,
        demand: d.daily_demand_hm3 ?? 0,
      })),
    [row?.days],
  );

  if (!proj?.available) {
    return (
      <section>
        <SectionHeader
          title="Proyección 7 días"
          description={proj?.note || "Sin proyección disponible."}
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Proyección 7 días"
        description={`${props.province} · ${proj.source ?? "Open-Meteo ET0"} · horizonte ${proj.horizon_days ?? 7} d`}
      />
      <Card className="mt-3 border-violet-600/20 dark:border-violet-400/25">
        <CardContent className="space-y-4 pt-4">
          {!row || row.available === false ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {row?.error || `Sin proyección para ${props.province}.`}
            </p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <div className="rounded-xl border border-amber-600/30 bg-amber-500/5 p-3 sm:col-span-1">
                  <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">Hasta crítico</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular-nums">
                    {row.days_until_critical === 0
                      ? "Ya crítico"
                      : row.days_until_critical != null
                        ? `${row.days_until_critical} d`
                        : "—"}
                  </p>
                  <p className="text-[11px] text-muted dark:text-muted-dark">
                    umbral &lt; {row.critical_threshold_days ?? props.autonomy.thresholds?.autonomy_critical_days ?? 21} d autonomía
                  </p>
                </div>
                <div className="rounded-xl border border-border/80 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">Autonomía hoy</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular-nums">{fmt(row.days_autonomy_start, " d", 0)}</p>
                </div>
                <div className="rounded-xl border border-violet-600/25 bg-violet-500/5 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">Autonomía a +7 d</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular-nums">{fmt(row.days_autonomy_end, " d", 0)}</p>
                  <p className="text-[11px] text-muted dark:text-muted-dark">{row.risk_level_end}</p>
                </div>
                <div className="rounded-xl border border-border/80 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">Demanda 7 d</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular-nums">{fmt(row.cumulative_demand_hm3, " hm³", 1)}</p>
                </div>
                <div className="rounded-xl border border-border/80 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">Embalse fin</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular-nums">{fmt(row.stored_end_hm3, " hm³", 0)}</p>
                  <p className="text-[11px] text-muted dark:text-muted-dark">desde {fmt(row.stored_start_hm3, "", 0)}</p>
                </div>
              </div>
              {chart.length > 0 ? (
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} width={36} />
                      <Tooltip />
                      <Area type="monotone" dataKey="days" name="Días autonomía" stroke="#7c3aed" fill="#8b5cf633" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : null}
            </>
          )}
          {proj.note ? (
            <p className="text-[11px] leading-relaxed text-muted dark:text-muted-dark">{proj.note}</p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
