import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  IrrigationAutonomySnapshot,
  SiarWaterBalanceProvince,
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

function bandLabel(band: string | undefined): string {
  switch (band) {
    case "dry":
      return "Seco";
    case "moderate":
      return "Moderado";
    case "mild":
      return "Suave";
    case "wet":
      return "Húmedo / cubierto";
    default:
      return "—";
  }
}

function bandClass(band: string | undefined): string {
  switch (band) {
    case "dry":
      return "border-rose-600/30 bg-rose-500/10 text-rose-900 dark:text-rose-100";
    case "moderate":
      return "border-amber-600/30 bg-amber-500/10 text-amber-950 dark:text-amber-100";
    case "mild":
      return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
    case "wet":
      return "border-emerald-600/25 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
    default:
      return "border-border bg-muted/30";
  }
}

function Kpi(props: {
  label: string;
  value: string;
  /** Plain-language what this number means. */
  explain: string;
  tone?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-3",
        props.tone ?? "border-border/80 bg-panel/40 dark:bg-panel-dark/40",
      )}
    >
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">{props.explain}</p>
    </div>
  );
}

export function SiarWaterBalancePanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const wb = props.autonomy.water_balance;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: SiarWaterBalanceProvince | null | undefined = useMemo(() => {
    if (!wb?.available) return null;
    if (isRegional) return wb.regional;
    return (wb.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [isRegional, wb, props.province]);

  const chart = useMemo(
    () =>
      (row?.series ?? []).map((d) => ({
        date: d.date.slice(5),
        et0: d.et0_mm ?? 0,
        precip: d.precip_mm ?? 0,
        balance: d.et0_minus_p_mm ?? 0,
      })),
    [row?.series],
  );

  if (!wb?.available) {
    return (
      <section>
        <SectionHeader
          title="Balance ET0 − P (SiAR)"
          description={
            wb?.note ||
            "Cuánto sobra o falta de agua atmosférica: si el cielo “pide” más evaporación de la que llueve."
          }
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Balance ET0 − P (SiAR)"
        description={
          wb.definition_es ||
          "Cuánto sobra o falta de agua atmosférica día a día. Sirve para explicar por qué se acelera el vaciado del embalse, aparte del déficit en hm³ de la autonomía."
        }
      />
      <Card className="mt-3 border-teal-600/20 dark:border-teal-400/25">
        <CardContent className="space-y-4 pt-4">
          {!row ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin serie SiAR de balance para {props.province}.
            </p>
          ) : (
            <>
              <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
                Lectura rápida para <span className="font-medium text-ink dark:text-ink-dark">{props.province}</span>
                {row.as_of ? ` · ${row.as_of}` : ""}. Un valor positivo en ET0 − P significa que ese día (o periodo)
                la evaporación potencial superó a la lluvia: el suelo y el cultivo “piden” más agua de la que cayó.
                No usa Kc ni hectáreas; eso ya está en la autonomía.
              </p>

              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium",
                    bandClass(row.band_7d),
                  )}
                >
                  Semana: {bandLabel(row.band_7d)}
                </span>
                <span className="text-xs text-muted dark:text-muted-dark">
                  Según la suma de ET0 − P de los últimos {row.days_in_7d ?? 7} días con dato.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Kpi
                  label="ET0 hoy"
                  value={fmt(row.et0_mm, " mm", 2)}
                  explain="Cuánta agua podría evaporarse hoy (Penman-Monteith SiAR). Es la “sed” del ambiente."
                />
                <Kpi
                  label="Precipitación hoy"
                  value={fmt(row.precip_mm, " mm", 2)}
                  explain="Lluvia medida hoy en las estaciones SiAR. Es lo que “entra” desde el cielo."
                />
                <Kpi
                  label="ET0 − P hoy"
                  value={fmt(row.et0_minus_p_mm, " mm", 2)}
                  explain="Si es positivo, hoy faltó lluvia respecto a la evaporación. Si es negativo o cero, la lluvia cubrió o superó esa sed."
                  tone="border-teal-600/30 bg-teal-500/5"
                />
                <Kpi
                  label="ET0 − Pe hoy"
                  value={fmt(row.et0_minus_pe_mm, " mm", 2)}
                  explain="Igual que arriba, pero con precipitación efectiva (Pe): la parte de la lluvia que suele quedar disponible para el cultivo."
                />
                <Kpi
                  label="Suma 7 d (ET0 − P)"
                  value={fmt(row.balance_7d_mm, " mm", 1)}
                  explain="Acumulado de la última semana. Si sube mucho, es una señal de que el vaciado del embalse puede acelerarse."
                  tone="border-teal-600/30 bg-teal-500/5"
                />
                <Kpi
                  label="Suma 30 d (ET0 − P)"
                  value={fmt(row.balance_30d_mm, " mm", 1)}
                  explain="Acumulado del último mes. Da contexto: un pico de un día pesa menos que varias semanas secas seguidas."
                />
              </div>

              {chart.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs text-muted dark:text-muted-dark">
                    Barras = ET0 − P (positivo = déficit atmosférico). Líneas = ET0 y precipitación diarias.
                  </p>
                  <div className="h-52 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} width={36} />
                        <Tooltip />
                        <Bar dataKey="balance" name="ET0 − P" fill="#0d9488" opacity={0.55} />
                        <Line
                          type="monotone"
                          dataKey="et0"
                          name="ET0"
                          stroke="#b45309"
                          strokeWidth={1.5}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="precip"
                          name="Precip"
                          stroke="#0284c7"
                          strokeWidth={1.5}
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : null}

              {(wb.by_province?.length ?? 0) > 0 ? (
                <div className="overflow-x-auto">
                  <p className="mb-2 text-xs font-medium text-muted dark:text-muted-dark">
                    Ranking provincial · suma 7 d de ET0 − P (quién está más “seco” esta semana)
                  </p>
                  <table className="w-full min-w-[420px] text-left text-sm">
                    <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                      <tr>
                        <th className="pb-2 font-medium">Provincia</th>
                        <th className="pb-2 font-medium">Hoy</th>
                        <th className="pb-2 font-medium">7 d</th>
                        <th className="pb-2 font-medium">30 d</th>
                        <th className="pb-2 font-medium">Semana</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...(wb.by_province ?? [])]
                        .sort(
                          (a, b) =>
                            (b.balance_7d_mm ?? -999) - (a.balance_7d_mm ?? -999),
                        )
                        .map((p) => (
                          <tr
                            key={p.province_name}
                            className="border-t border-black/5 dark:border-white/5"
                          >
                            <td className="py-2 font-medium">{p.province_name}</td>
                            <td className="py-2 tabular-nums">{fmt(p.et0_minus_p_mm, "", 1)}</td>
                            <td className="py-2 tabular-nums font-semibold">
                              {fmt(p.balance_7d_mm, "", 1)}
                            </td>
                            <td className="py-2 tabular-nums">{fmt(p.balance_30d_mm, "", 1)}</td>
                            <td className="py-2">
                              <span
                                className={cn(
                                  "rounded-full border px-2 py-0.5 text-[11px] font-medium",
                                  bandClass(p.band_7d),
                                )}
                              >
                                {bandLabel(p.band_7d)}
                              </span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
