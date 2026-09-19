import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  IrrigationAutonomyProvince,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
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

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function levelLabel(level: string): string {
  switch (level) {
    case "critical":
      return "Crítico (<30 d)";
    case "warning":
      return "Alerta (<60 d)";
    case "watch":
      return "Vigilancia (<120 d)";
    case "ok":
      return "Holgado (≥120 d)";
    default:
      return "Sin dato";
  }
}

function levelClass(level: string): string {
  switch (level) {
    case "critical":
      return "border-rose-600/30 bg-rose-500/10 text-rose-800 dark:text-rose-200";
    case "warning":
      return "border-amber-600/30 bg-amber-500/10 text-amber-900 dark:text-amber-100";
    case "watch":
      return "border-sky-600/25 bg-sky-500/10 text-sky-900 dark:text-sky-100";
    case "ok":
      return "border-emerald-600/25 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100";
    default:
      return "border-border bg-muted/30";
  }
}

function barColor(level: string): string {
  switch (level) {
    case "critical":
      return "#e11d48";
    case "warning":
      return "#d97706";
    case "watch":
      return "#0284c7";
    case "ok":
      return "#059669";
    default:
      return "#94a3b8";
  }
}

function Kpi(props: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div
      className={`rounded-xl border p-3 ${
        props.tone ?? "border-border/80 bg-panel/40 dark:bg-panel-dark/40"
      }`}
    >
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      {props.hint ? <p className="mt-0.5 text-[11px] text-muted dark:text-muted-dark">{props.hint}</p> : null}
    </div>
  );
}

export function IrrigationAutonomyPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const a = props.autonomy;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: IrrigationAutonomyProvince | null | undefined = useMemo(() => {
    if (isRegional) return a.regional;
    return (a.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [a.by_province, a.regional, isRegional, props.province]);

  const chart = useMemo(
    () =>
      [...(a.by_province ?? [])]
        .sort((x, y) => (x.days_autonomy ?? 0) - (y.days_autonomy ?? 0))
        .map((p) => ({
          name: p.province_name.slice(0, 3),
          full: p.province_name,
          days: p.days_autonomy ?? 0,
          level: p.risk_level,
        })),
    [a.by_province],
  );

  if (!a.available) {
    return (
      <section>
        <SectionHeader
          title="Autonomía de riego"
          description={a.note || "Piloto embalse ÷ demanda SiAR (aún sin datos)."}
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Autonomía de riego"
        description={`Piloto · ${props.province} · embalses ${a.as_of_reservoir ?? "—"} · SiAR ${a.as_of_siar ?? "—"} · Kc=${a.kc ?? 0.75}`}
      />
      <Card className="mt-3 border-amber-600/20 dark:border-amber-400/25">
        <CardContent className="space-y-4 pt-4">
          {!row ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin cálculo para {props.province}.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full border px-2.5 py-1 text-xs font-medium ${levelClass(row.risk_level)}`}
                >
                  {levelLabel(row.risk_level)}
                </span>
                <span className="text-xs text-muted dark:text-muted-dark">
                  Orientativo: no descuenta abastecimiento urbano ni derechos de riego.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Kpi
                  label="Días de autonomía"
                  value={fmt(row.days_autonomy, " d", 0)}
                  hint={fmt(row.weeks_autonomy, " semanas", 1)}
                  tone={levelClass(row.risk_level)}
                />
                <Kpi label="Embalsado" value={fmt(row.stored_hm3, " hm³", 0)} hint={`Llenado ${fmt(row.fill_pct, " %", 0)}`} />
                <Kpi label="Demanda día" value={fmt(row.daily_demand_hm3, " hm³", 2)} hint={`Neto ${fmt(row.net_demand_mm, " mm")}`} />
                <Kpi label="ET0 SiAR" value={fmt(row.et0_mm, " mm")} hint={`Pe ${fmt(row.pe_mm, " mm")}`} />
                <Kpi label="Regadío" value={fmt(row.irrigated_ha, " ha", 0)} hint="Junta 2023" />
                <Kpi label="Estaciones SiAR" value={String(row.siar_station_count)} />
              </div>
            </>
          )}

          {chart.length > 0 ? (
            <div>
              <p className="mb-2 text-xs font-medium text-muted dark:text-muted-dark">
                Ranking provincial (días de autonomía)
              </p>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} width={36} />
                    <Tooltip
                      formatter={(value: number | string) => [`${value} d`, "Autonomía"]}
                      labelFormatter={(_, payload) => {
                        const row = payload?.[0]?.payload as { full?: string } | undefined;
                        return row?.full ?? "";
                      }}
                    />
                    <Bar dataKey="days" radius={[4, 4, 0, 0]}>
                      {chart.map((d) => (
                        <Cell key={d.full} fill={barColor(d.level)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {a.note ? (
            <p className="text-[11px] leading-relaxed text-muted dark:text-muted-dark">{a.note}</p>
          ) : null}
          {a.method_es ? (
            <p className="text-[11px] leading-relaxed text-muted dark:text-muted-dark">{a.method_es}</p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
