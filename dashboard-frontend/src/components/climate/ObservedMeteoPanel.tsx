import { useMemo } from "react";
import { weatherEmoji } from "@/components/climate/weatherIcons";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import { cn } from "@/lib/utils";
import { chartToneForId } from "@/lib/water-chart";
import type { MeteoObservedMetrics, MeteoObservedSnapshot } from "@/types/dashboard-model";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function Kpi(props: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-black/5 bg-white/60 p-3 dark:border-white/10 dark:bg-white/5">
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      {props.hint ? <p className="mt-0.5 text-[11px] text-muted dark:text-muted-dark">{props.hint}</p> : null}
    </div>
  );
}

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

export function ObservedMeteoPanel(props: {
  meteo: MeteoObservedSnapshot;
  province: ClimateProvince;
}) {
  const m = props.meteo;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const r: MeteoObservedMetrics | null | undefined = useMemo(() => {
    if (isRegional) return m.regional;
    return (m.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [isRegional, m.by_province, m.regional, props.province]);

  const tempTone = chartToneForId("temp_anomaly");
  const humidTone = chartToneForId("fill");

  const trendSource = useMemo(() => {
    if (isRegional) return m.trend_days ?? [];
    return m.trend_by_province?.[props.province] ?? [];
  }, [isRegional, m.trend_by_province, m.trend_days, props.province]);

  const series = trendSource.map((d) => ({
    date: d.date.slice(5),
    temp: d.mean_temp_c,
    humidity: d.mean_humidity_pct,
    precip: d.precip_mm,
  }));

  const scopeHint = isRegional ? "Media regional del día" : `Media provincial · ${props.province}`;

  return (
    <section className="space-y-3">
      <SectionHeader
        title="Observado RIA"
        description="Variables del día más reciente en estaciones RIA (grano diario). No es un parte a tiempo real ni un pronóstico."
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-4xl" aria-hidden>
              {weatherEmoji(r?.condition)}
            </span>
            <div>
              <p className="font-display text-lg font-semibold text-ink dark:text-ink-dark">
                {r?.condition_label_es ?? "Sin condición"}
              </p>
              <p className="text-sm text-muted dark:text-muted-dark">
                {props.province} · Último día:{" "}
                <span className="tabular-nums">{m.as_of ?? "—"}</span>
                {m.grain ? ` · ${m.grain}` : null}
              </p>
            </div>
          </div>

          {!m.available || !r ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin observaciones RIA recientes{isRegional ? "" : ` para ${props.province}`}.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <Kpi
                label="Temperatura"
                value={fmt(r.mean_temp_c, " °C")}
                hint={`Máx ${fmt(r.max_temp_c)} / Mín ${fmt(r.min_temp_c)}`}
              />
              <Kpi label="Sensación (est.)" value={fmt(r.feels_like_c, " °C")} hint="Heat index aprox." />
              <Kpi label="Humedad" value={fmt(r.mean_humidity_pct, " %", 0)} />
              <Kpi
                label="Viento"
                value={fmt(r.mean_wind_speed, " m/s", 2)}
                hint={r.wind_dir_label ? `Dir. ${r.wind_dir_label}` : undefined}
              />
              <Kpi label="Precipitación" value={fmt(r.precip_mm, " mm", 2)} hint={scopeHint} />
              <Kpi label="ET0" value={fmt(r.et0_mm, " mm", 2)} hint="Evapotranspiración ref." />
            </div>
          )}

          {(m.alerts ?? []).length > 0 && isRegional ? (
            <ul className="flex flex-wrap gap-2">
              {(m.alerts ?? []).map((a) => (
                <li
                  key={`${a.code}-${a.title_es}`}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    a.severity === "critical" && "bg-red-600/15 text-red-800 dark:text-red-200",
                    a.severity === "warning" && "bg-amber-500/15 text-amber-900 dark:text-amber-100",
                    a.severity === "info" && "bg-sky-500/15 text-sky-900 dark:text-sky-100",
                  )}
                  title={a.detail_es}
                >
                  {a.title_es}
                </li>
              ))}
            </ul>
          ) : null}

          {series.length > 1 ? (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div>
                <p className="mb-1 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                  Temperatura media · últimos {series.length} días
                </p>
                <div className="h-28 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                      <defs>
                        <linearGradient id="obs-temp-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={tempTone.fillTop} />
                          <stop offset="100%" stopColor={tempTone.fillBottom} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                      <YAxis tick={{ fontSize: 10 }} width={32} domain={["auto", "auto"]} />
                      <Tooltip formatter={(v) => [`${Number(v).toFixed(1)} °C`, "Temp"]} />
                      <Area
                        type="monotone"
                        dataKey="temp"
                        stroke={tempTone.stroke}
                        fill="url(#obs-temp-fill)"
                        strokeWidth={1.5}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div>
                <p className="mb-1 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                  Humedad media · últimos {series.length} días
                </p>
                <div className="h-28 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                      <defs>
                        <linearGradient id="obs-hum-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={humidTone.fillTop} />
                          <stop offset="100%" stopColor={humidTone.fillBottom} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                      <YAxis tick={{ fontSize: 10 }} width={32} domain={[0, 100]} />
                      <Tooltip formatter={(v) => [`${Number(v).toFixed(0)} %`, "Humedad"]} />
                      <Area
                        type="monotone"
                        dataKey="humidity"
                        stroke={humidTone.stroke}
                        fill="url(#obs-hum-fill)"
                        strokeWidth={1.5}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ) : null}

          {m.note ? <p className="text-xs text-muted dark:text-muted-dark">{m.note}</p> : null}
        </CardContent>
      </Card>
    </section>
  );
}
