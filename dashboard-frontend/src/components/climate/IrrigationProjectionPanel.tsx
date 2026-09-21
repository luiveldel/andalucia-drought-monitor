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

function Kpi(props: { label: string; value: string; explain: string; hint?: string; tone?: string }) {
  return (
    <div className={`rounded-xl border p-3 ${props.tone ?? "border-border/80"}`}>
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums">{props.value}</p>
      {props.hint ? <p className="text-[11px] text-muted dark:text-muted-dark">{props.hint}</p> : null}
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">{props.explain}</p>
    </div>
  );
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
          description={
            proj?.note ||
            "Adelanta cómo evolucionarían autonomía y embalse si la demanda sigue al ritmo del pronóstico de ET0."
          }
        />
      </section>
    );
  }

  const crit =
    row?.critical_threshold_days ??
    props.autonomy.thresholds?.autonomy_critical_days ??
    21;

  return (
    <section>
      <SectionHeader
        title="Proyección 7 días"
        description="Simula la próxima semana: restamos cada día la demanda estimada (con ET0 de Open-Meteo) del embalse usable. Así vemos si nos acercamos al crítico."
      />
      <Card className="mt-3 border-violet-600/20 dark:border-violet-400/25">
        <CardContent className="space-y-4 pt-4">
          {!row || row.available === false ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {row?.error || `Sin proyección para ${props.province}.`}
            </p>
          ) : (
            <>
              <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
                Ámbito <span className="font-medium text-ink dark:text-ink-dark">{props.province}</span>
                {" · "}
                {proj.source ?? "Open-Meteo ET0"} · horizonte {proj.horizon_days ?? 7} d. No es un
                balance oficial de derechos; es un escenario meteorológico de demanda.
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <Kpi
                  label="Hasta crítico"
                  value={
                    row.days_until_critical === 0
                      ? "Ya crítico"
                      : row.days_until_critical != null
                        ? `${row.days_until_critical} d`
                        : "—"
                  }
                  hint={`umbral < ${crit} d autonomía`}
                  explain="Días de calendario hasta caer por debajo del umbral crítico, según esta proyección."
                  tone="border-amber-600/30 bg-amber-500/5"
                />
                <Kpi
                  label="Autonomía hoy"
                  value={fmt(row.days_autonomy_start, " d", 0)}
                  explain="Punto de partida: días de riego que hay ahora con el embalse usable."
                />
                <Kpi
                  label="Autonomía a +7 d"
                  value={fmt(row.days_autonomy_end, " d", 0)}
                  hint={row.risk_level_end ?? undefined}
                  explain="Cómo quedaría ese colchón dentro de una semana si se cumple el pronóstico de ET0 y lluvia."
                  tone="border-violet-600/25 bg-violet-500/5"
                />
                <Kpi
                  label="Demanda 7 d"
                  value={fmt(row.cumulative_demand_hm3, " hm³", 1)}
                  explain="Agua total que pediría el regadío en esos 7 días, sumando cada día."
                />
                <Kpi
                  label="Embalse fin"
                  value={fmt(row.stored_end_hm3, " hm³", 0)}
                  hint={`desde ${fmt(row.stored_start_hm3, "", 0)}`}
                  explain="Volumen usable estimado al final de la semana tras restar esa demanda."
                />
              </div>
              {chart.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs text-muted dark:text-muted-dark">
                    Curva de autonomía día a día en el horizonte de 7 días.
                  </p>
                  <div className="h-48 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} width={36} />
                        <Tooltip />
                        <Area
                          type="monotone"
                          dataKey="days"
                          name="Días autonomía"
                          stroke="#7c3aed"
                          fill="#8b5cf633"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
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
