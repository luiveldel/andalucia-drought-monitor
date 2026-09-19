import { weatherEmoji } from "@/components/climate/weatherIcons";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { MeteoForecastSnapshot } from "@/types/dashboard-model";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function hourLabel(iso: string): string {
  const part = iso.includes("T") ? iso.split("T")[1] : iso;
  return (part ?? "").slice(0, 5);
}

export function ForecastPanel(props: { forecast: MeteoForecastSnapshot }) {
  const f = props.forecast;
  const c = f.current;

  return (
    <section className="space-y-3">
      <SectionHeader
        title={`Pronóstico ${f.source || "externo"}`}
        description={`${f.location_label ?? ""} · fuente externa (no RIA). Horario del día en curso y resumen a 7 días.`}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          {!f.available || !c ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Pronóstico no disponible{f.error ? `: ${f.error}` : "."}
            </p>
          ) : (
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
                    <span className="tabular-nums font-medium">{fmt(c.precip_probability, " %", 0)}</span>
                  </p>
                  <p>
                    <span className="text-muted dark:text-muted-dark">Presión </span>
                    <span className="tabular-nums font-medium">{fmt(c.pressure_hpa, " hPa", 0)}</span>
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
                        (c.uv_index ?? 0) >= 6 && (c.uv_index ?? 0) < 8 && "text-amber-700 dark:text-amber-200",
                      )}
                    >
                      {fmt(c.uv_index, "", 1)}
                    </span>
                  </p>
                </div>
              </div>

              {(f.alerts ?? []).length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {f.alerts.map((a) => (
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

              {(f.hourly_today ?? []).length > 0 ? (
                <div>
                  <p className="mb-2 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    Hoy por horas
                  </p>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {f.hourly_today.map((h) => (
                      <div
                        key={h.time}
                        className="min-w-[4.25rem] shrink-0 rounded-xl border border-black/5 bg-white/50 px-2 py-2 text-center dark:border-white/10 dark:bg-white/5"
                      >
                        <p className="text-[11px] tabular-nums text-muted dark:text-muted-dark">
                          {hourLabel(h.time)}
                        </p>
                        <p className="text-lg" aria-hidden>
                          {weatherEmoji(h.condition)}
                        </p>
                        <p className="text-sm font-semibold tabular-nums">{fmt(h.temp_c, "°", 0)}</p>
                        <p className="text-[10px] tabular-nums text-sky-700 dark:text-sky-300">
                          {fmt(h.precip_probability, "%", 0)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {(f.daily ?? []).length > 0 ? (
                <div>
                  <p className="mb-2 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    Próximos 7 días
                  </p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
                    {f.daily.map((d) => (
                      <div
                        key={d.date}
                        className="rounded-xl border border-black/5 bg-white/50 p-2.5 dark:border-white/10 dark:bg-white/5"
                      >
                        <p className="text-[11px] tabular-nums text-muted dark:text-muted-dark">
                          {d.date.slice(5)}
                        </p>
                        <p className="my-1 text-2xl" aria-hidden>
                          {weatherEmoji(d.condition)}
                        </p>
                        <p className="text-sm font-semibold tabular-nums">
                          {fmt(d.t_max, "°", 0)} / {fmt(d.t_min, "°", 0)}
                        </p>
                        <p className="mt-1 text-[11px] text-muted dark:text-muted-dark">
                          {d.condition_label_es}
                        </p>
                        <p className="text-[11px] tabular-nums text-sky-700 dark:text-sky-300">
                          {fmt(d.precip_sum, " mm", 1)} · UV {fmt(d.uv_index_max, "", 0)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </>
          )}

          <p className="text-xs text-muted dark:text-muted-dark">
            Datos de{" "}
            <a
              className="underline underline-offset-2"
              href={f.attribution || "https://opendata.aemet.es/"}
              target="_blank"
              rel="noreferrer"
            >
              {f.source || "fuente externa"}
            </a>
            {f.error ? ` · ${f.error}` : null}
            {f.generated_at ? ` · actualizado ${f.generated_at.slice(0, 16).replace("T", " ")}` : null}
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
