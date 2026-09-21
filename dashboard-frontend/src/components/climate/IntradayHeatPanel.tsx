import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  IntradayHeatScope,
  IntradayHeatSnapshot,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function fmt(n: number | null | undefined, digits = 1, unit = ""): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function Kpi(props: {
  label: string;
  value: string;
  explain: string;
  tone?: string;
}) {
  return (
    <div className={cn("rounded-xl border p-3", props.tone ?? "border-border/80")}>
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
        {props.label}
      </p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">
        {props.explain}
      </p>
    </div>
  );
}

export function IntradayHeatPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const snap: IntradayHeatSnapshot | undefined = props.autonomy.intraday_heat;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: IntradayHeatScope | null | undefined = useMemo(() => {
    if (!snap?.available) return null;
    if (isRegional) return snap.regional ?? null;
    return (snap.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [snap, isRegional, props.province]);

  const chart = useMemo(() => {
    const series = row?.series ?? [];
    const dates = [...new Set(series.map((h) => h.date).filter(Boolean))] as string[];
    const last = dates.sort().at(-1);
    const daySeries = last ? series.filter((h) => h.date === last) : series;
    return daySeries.map((h) => ({
      hour: h.hour_label ?? (h.time ?? "").slice(11, 16),
      temp: h.temp_c ?? null,
      rh: h.humidity_pct ?? null,
    }));
  }, [row]);

  const heatThreshold = snap?.thresholds?.heat_temp_c ?? 35;
  const sourceIsProxy =
    (snap?.source || "").includes("open_meteo") || (snap?.source || "").includes("proxy");

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title="Olas de calor intradía"
          description={
            snap?.note_es ||
            "Curva horaria de temperatura y horas de estrés térmico: más fina que la media diaria para ver picos que disparan la demanda de riego."
          }
        />
        <Card className="mt-3">
          <CardContent className="pt-4 text-sm text-muted dark:text-muted-dark">
            Aún no hay curva intradía. Con SiAR horario (tabla raw) o el proxy Open-Meteo
            etiquetado aparecerá aquí.
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Olas de calor intradía"
        description={
          snap.definition_es ||
          "Horas con T > 35 °C y HR < 30 %. La media diaria puede ocultar el pico de la tarde."
        }
      />
      <Card
        className={cn(
          "mt-3",
          sourceIsProxy
            ? "border-amber-600/25 dark:border-amber-400/25"
            : "border-orange-600/20 dark:border-orange-400/25",
        )}
      >
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 font-medium",
                sourceIsProxy
                  ? "border-amber-600/40 bg-amber-500/10 text-amber-950 dark:text-amber-100"
                  : "border-emerald-600/40 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100",
              )}
            >
              {snap.source_label_es || snap.source}
            </span>
            {snap.as_of ? (
              <span className="text-muted dark:text-muted-dark">hasta {snap.as_of}</span>
            ) : null}
            {sourceIsProxy ? (
              <span className="text-amber-800 dark:text-amber-200">
                Proxy etiquetado — no es estación SiAR
              </span>
            ) : null}
          </div>

          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {snap.headline_es}
          </p>

          {!row ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin serie para {props.province} en la ventana.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                <Kpi
                  label="Horas de estrés"
                  value={`${row.heat_hours ?? 0}`}
                  explain={`T > ${heatThreshold} °C y HR < ${snap.thresholds?.heat_rh_pct ?? 30} % (mismo criterio que el diario).`}
                  tone="border-rose-600/30 bg-rose-500/5"
                />
                <Kpi
                  label="Horas elevadas"
                  value={`${row.elevated_hours ?? 0}`}
                  explain={`T ≥ ${snap.thresholds?.elevated_temp_c ?? 32} °C: calor que ya empuja la demanda.`}
                  tone="border-orange-600/30 bg-orange-500/5"
                />
                <Kpi
                  label="Media horaria"
                  value={fmt(row.temp_mean_c, 1, " °C")}
                  explain="Lo que vería un resumen diario si solo mirara la media."
                />
                <Kpi
                  label="Pico intradía"
                  value={fmt(row.temp_peak_c, 1, " °C")}
                  explain={`+${fmt(row.peak_minus_mean_c, 1)} °C sobre la media: el empujón de la tarde.`}
                  tone="border-orange-600/30 bg-orange-500/5"
                />
                <Kpi
                  label="ET0 acum. (h)"
                  value={fmt(row.et0_sum_mm, 2, " mm")}
                  explain="Suma de ET0 horaria en la ventana (SiAR o FAO Open-Meteo)."
                />
              </div>

              <p className="text-sm leading-relaxed text-ink/90 dark:text-ink-dark/90">
                {row.plain_es}
              </p>

              {chart.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chart} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                      <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                      <YAxis
                        yAxisId="temp"
                        tick={{ fontSize: 11 }}
                        unit="°"
                        domain={["auto", "auto"]}
                      />
                      <YAxis
                        yAxisId="rh"
                        orientation="right"
                        tick={{ fontSize: 11 }}
                        unit="%"
                        domain={[0, 100]}
                      />
                      <Tooltip
                        contentStyle={{ fontSize: 12 }}
                        formatter={(value: number, name: string) => {
                          if (name === "temp") return [`${Number(value).toFixed(1)} °C`, "Temp."];
                          if (name === "rh") return [`${Number(value).toFixed(0)} %`, "Humedad"];
                          return [value, name];
                        }}
                      />
                      <ReferenceLine
                        yAxisId="temp"
                        y={heatThreshold}
                        stroke="#e11d48"
                        strokeDasharray="4 4"
                        label={{ value: `T>${heatThreshold}`, fontSize: 10, fill: "#e11d48" }}
                      />
                      <Area
                        yAxisId="temp"
                        type="monotone"
                        dataKey="temp"
                        name="temp"
                        stroke="#ea580c"
                        fill="#fb923c33"
                        strokeWidth={2}
                      />
                      <Line
                        yAxisId="rh"
                        type="monotone"
                        dataKey="rh"
                        name="rh"
                        stroke="#0284c7"
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              ) : null}

              {snap.note_es ? (
                <p className="text-xs text-muted dark:text-muted-dark">{snap.note_es}</p>
              ) : null}
              {(snap.caveats_es ?? []).length > 0 ? (
                <ul className="list-disc space-y-1 pl-5 text-[11px] text-muted dark:text-muted-dark">
                  {(snap.caveats_es ?? []).map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
