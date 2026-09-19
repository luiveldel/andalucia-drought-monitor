import { useEffect, useState } from "react";
import { weatherEmoji } from "@/components/climate/weatherIcons";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import { cn } from "@/lib/utils";
import { fetchMeteoForecast } from "@/services/dashboard/dashboard.service";
import type { MeteoForecastSnapshot } from "@/types/dashboard-model";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function hourLabel(iso: string): string {
  const part = iso.includes("T") ? iso.split("T")[1] : iso;
  return (part ?? "").slice(0, 5);
}

export function ForecastPanel(props: {
  /** Baseline forecast from the dashboard payload (Andalucía). */
  forecast: MeteoForecastSnapshot;
  province: ClimateProvince;
}) {
  const [live, setLive] = useState<MeteoForecastSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (props.province === CLIMATE_REGIONAL) {
      setLive(null);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    void fetchMeteoForecast(props.province)
      .then((data) => {
        if (!cancelled) setLive(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Error de forecast");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [props.province]);

  const f = props.province === CLIMATE_REGIONAL ? props.forecast : (live ?? props.forecast);
  const c = f.current;

  return (
    <section className="space-y-3">
      <SectionHeader
        title={`Pronóstico ${f.source || "externo"}`}
        description={`${f.location_label ?? props.province} · fuente externa (no RIA). Horario del día en curso y resumen a 7 días.`}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          {loading ? (
            <p className="text-sm text-muted dark:text-muted-dark">Cargando pronóstico de {props.province}…</p>
          ) : null}
          {error ? <p className="text-sm text-sev-critical">{error}</p> : null}
          {!loading && (!f.available || !c) ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Pronóstico no disponible{f.error ? `: ${f.error}` : "."}
            </p>
          ) : null}
          {!loading && f.available && c ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-4xl" aria-hidden>
                    {weatherEmoji(c.condition)}
                  </span>
                  <div>
                    <p className="font-display text-3xl font-semibold tabular-nums">
                      {fmt(c.temp_c, " °C")}
                    </p>
                    <p className="text-sm text-muted dark:text-muted-dark">
                      {c.condition_label_es} · sensación {fmt(c.feels_like_c, " °C")}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
                  <p>
                    <span className="text-muted dark:text-muted-dark">Humedad </span>
                    <span className="tabular-nums font-medium">{fmt(c.humidity_pct, " %", 0)}</span>
                  </p>
                  <p>
                    <span className="text-muted dark:text-muted-dark">Prob. lluvia </span>
                    <span className="tabular-nums font-medium">
                      {fmt(c.precip_probability, " %", 0)}
                    </span>
                  </p>
                  <p>
                    <span className="text-muted dark:text-muted-dark">Presión </span>
                    <span className="tabular-nums font-medium">{fmt(c.pressure_hpa, " hPa", 0)}</span>
                    {c.pressure_source ? (
                      <span className="ml-1 text-[10px] text-muted dark:text-muted-dark">
                        ({c.pressure_source})
                      </span>
                    ) : null}
                  </p>
                  <p>
                    <span className="text-muted dark:text-muted-dark">Viento </span>
                    <span className="tabular-nums font-medium">{fmt(c.wind_speed, " km/h", 0)}</span>
                  </p>
                  <p>
                    <span className="text-muted dark:text-muted-dark">UV </span>
                    <span
                      className={cn(
                        "tabular-nums font-medium",
                        (c.uv_index ?? 0) >= 8 && "text-red-700 dark:text-red-300",
                        (c.uv_index ?? 0) >= 6 &&
                          (c.uv_index ?? 0) < 8 &&
                          "text-amber-700 dark:text-amber-200",
                      )}
                    >
                      {fmt(c.uv_index, "", 1)}
                    </span>
                  </p>
                </div>
              </div>

              {((f.hourly_today ?? []).length > 0) ? (
                <div>
                  <p className="mb-2 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    Hoy (horario)
                  </p>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {(f.hourly_today ?? []).map((h) => (
                      <div
                        key={h.time}
                        className="min-w-[4.5rem] rounded-lg border border-black/5 px-2 py-2 text-center dark:border-white/10"
                      >
                        <p className="text-[10px] text-muted dark:text-muted-dark">{hourLabel(h.time)}</p>
                        <p className="text-lg" aria-hidden>
                          {weatherEmoji(h.condition)}
                        </p>
                        <p className="text-sm font-semibold tabular-nums">{fmt(h.temp_c, "°", 0)}</p>
                        <p className="text-[10px] tabular-nums text-muted dark:text-muted-dark">
                          {fmt(h.precip_probability, "%", 0)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {((f.daily ?? []).length > 0) ? (
                <div>
                  <p className="mb-2 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    Próximos días
                  </p>
                  <ul className="divide-y divide-black/5 dark:divide-white/10">
                    {(f.daily ?? []).map((d) => (
                      <li key={d.date} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <span className="w-24 tabular-nums text-muted dark:text-muted-dark">
                          {d.date.slice(5)}
                        </span>
                        <span className="text-lg" aria-hidden>
                          {weatherEmoji(d.condition)}
                        </span>
                        <span className="flex-1 text-muted dark:text-muted-dark">
                          {d.condition_label_es}
                        </span>
                        <span className="tabular-nums font-medium">
                          {fmt(d.t_min, "°", 0)} / {fmt(d.t_max, "°", 0)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
