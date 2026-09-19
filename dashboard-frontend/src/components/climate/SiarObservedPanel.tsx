import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type { MeteoSiarMetrics, MeteoSiarSnapshot } from "@/types/dashboard-model";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { chartToneForId } from "@/lib/water-chart";

function Kpi(props: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-emerald-600/15 bg-emerald-500/5 p-3 dark:border-emerald-400/20 dark:bg-emerald-400/5">
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

export function SiarObservedPanel(props: {
  meteo: MeteoSiarSnapshot;
  province: ClimateProvince;
}) {
  const m = props.meteo;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const r: MeteoSiarMetrics | null | undefined = useMemo(() => {
    if (isRegional) return m.regional;
    return (m.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [isRegional, m.by_province, m.regional, props.province]);

  const series = useMemo(
    () =>
      (m.trend_days ?? []).map((d) => ({
        date: d.date.slice(5),
        temp: d.mean_temp_c,
        et0: d.et0_mm ?? 0,
      })),
    [m.trend_days],
  );

  const et0Tone = chartToneForId("deficit");

  if (!m.available) {
    return (
      <section>
        <SectionHeader
          title="SiAR · MAPA"
          description={m.note || "Red de riego del Ministerio (aún sin datos)."}
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="SiAR · MAPA"
        description={`Estaciones de riego · ${props.province}${m.as_of ? ` · ${m.as_of}` : ""} · ${m.station_count ?? r?.station_count ?? "—"} estaciones`}
      />
      <Card className="mt-3 border-emerald-600/20 dark:border-emerald-400/25">
        <CardContent className="space-y-4 pt-4">
          {!r ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin estaciones SiAR para {props.province} en la fecha disponible.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Kpi label="T media" value={fmt(r.mean_temp_c, " °C")} hint={`${fmt(r.min_temp_c)} / ${fmt(r.max_temp_c)}`} />
              <Kpi label="Humedad" value={fmt(r.mean_humidity_pct, " %", 0)} />
              <Kpi label="Precipitación" value={fmt(r.precip_mm, " mm", 2)} />
              <Kpi label="ET0" value={fmt(r.et0_mm, " mm", 2)} hint="Penman-Monteith" />
              <Kpi label="Radiación" value={fmt(r.solar_radiation, "", 1)} />
              <Kpi
                label="Viento"
                value={fmt(r.mean_wind_speed, " m/s", 2)}
                hint={r.wind_dir_label ? `Dir. ${r.wind_dir_label}` : undefined}
              />
            </div>
          )}

          {series.length > 1 ? (
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                ET0 regional · últimos {series.length} días
              </p>
              <div className="h-28 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                    <defs>
                      <linearGradient id="siar-et0-fill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={et0Tone.fillTop} />
                        <stop offset="100%" stopColor={et0Tone.fillBottom} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10 }} width={32} domain={["auto", "auto"]} />
                    <Tooltip formatter={(v) => [`${Number(v).toFixed(2)} mm`, "ET0"]} />
                    <Area
                      type="monotone"
                      dataKey="et0"
                      stroke={et0Tone.stroke}
                      fill="url(#siar-et0-fill)"
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {m.note ? <p className="text-xs text-muted dark:text-muted-dark">{m.note}</p> : null}
        </CardContent>
      </Card>
    </section>
  );
}
