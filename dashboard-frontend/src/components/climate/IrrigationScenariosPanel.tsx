import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import { cn } from "@/lib/utils";
import type {
  IrrigationAutonomySnapshot,
  IrrigationProjectionProvince,
  IrrigationScenarioRun,
} from "@/types/dashboard-model";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
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

function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  return d.slice(0, 10);
}

function Kpi(props: { label: string; value: string; explain: string; tone?: string }) {
  return (
    <div className={`rounded-xl border p-3 ${props.tone ?? "border-border/80"}`}>
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
        {props.label}
      </p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums">{props.value}</p>
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">
        {props.explain}
      </p>
    </div>
  );
}

function pickRow(
  run: IrrigationScenarioRun | undefined,
  province: ClimateProvince,
): IrrigationProjectionProvince | null {
  if (!run?.available) return null;
  if (province === CLIMATE_REGIONAL) return run.regional ?? null;
  return (run.by_province ?? []).find((p) => p.province_name === province) ?? null;
}

export function IrrigationScenariosPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const snap = props.autonomy.scenarios;
  const modes = snap?.modes ?? [];
  const horizons = snap?.horizons ?? [7, 14, 21];
  const [mode, setMode] = useState<string>(modes[0]?.id ?? "baseline");
  const [horizon, setHorizon] = useState<number>(horizons[0] ?? 7);

  const run: IrrigationScenarioRun | undefined = snap?.by_mode?.[mode]?.[String(horizon)];
  const baselineRun = snap?.by_mode?.baseline?.[String(horizon)];
  const dryRun = snap?.by_mode?.dry_high_et0?.[String(horizon)];

  const row = useMemo(() => pickRow(run, props.province), [run, props.province]);
  const baseRow = useMemo(
    () => pickRow(baselineRun, props.province),
    [baselineRun, props.province],
  );
  const dryRow = useMemo(() => pickRow(dryRun, props.province), [dryRun, props.province]);

  const chart = useMemo(() => {
    const bDays = baseRow?.days ?? [];
    const dDays = dryRow?.days ?? [];
    const n = Math.max(bDays.length, dDays.length);
    const out: Array<{ date: string; baseline?: number; dry?: number }> = [];
    for (let i = 0; i < n; i++) {
      const bd = bDays[i];
      const dd = dDays[i];
      out.push({
        date: (bd?.date ?? dd?.date ?? "").slice(5),
        baseline: bd?.days_autonomy ?? undefined,
        dry: dd?.days_autonomy ?? undefined,
      });
    }
    return out;
  }, [baseRow, dryRow]);

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title="Escenarios de riego"
          description={
            snap?.note_es ||
            "Si el calor se mantiene y no llueve, ¿cuándo se acerca el crítico? Compara pronóstico y escenario seco."
          }
        />
      </section>
    );
  }

  const modeMeta = modes.find((m) => m.id === mode);

  return (
    <section>
      <SectionHeader
        title="Escenarios de riego"
        description="¿Qué pasa si se cumple el pronóstico… o si no llueve y la ET0 sube? Proyectamos autonomía y embalse usable a 7, 14 o 21 días."
      />
      <Card className="mt-3 border-violet-600/20 dark:border-violet-400/25">
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Modo de escenario">
              {modes.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setMode(m.id)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    mode === m.id
                      ? "bg-violet-600/15 text-violet-900 dark:bg-violet-400/20 dark:text-violet-100"
                      : "bg-black/5 text-muted hover:text-ink dark:bg-white/5 dark:text-muted-dark dark:hover:text-ink-dark",
                  )}
                >
                  {m.label_es}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Horizonte">
              {horizons.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHorizon(h)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium tabular-nums transition-colors",
                    horizon === h
                      ? "bg-terracotta/15 text-terracotta dark:bg-terracotta-dark/20 dark:text-terracotta-dark"
                      : "bg-black/5 text-muted hover:text-ink dark:bg-white/5 dark:text-muted-dark dark:hover:text-ink-dark",
                  )}
                >
                  {h} d
                </button>
              ))}
            </div>
          </div>

          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            Ámbito <span className="font-medium text-ink dark:text-ink-dark">{props.province}</span>
            {" · "}
            {modeMeta?.describe_es ?? snap.source ?? "Open-Meteo"}
            {run?.extrapolated_beyond_om
              ? " · tramo final extrapolado con la media del pronóstico"
              : null}
          </p>

          {!row || row.available === false ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {row?.error || `Sin escenario para ${props.province}.`}
            </p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Kpi
                  label="Hasta crítico"
                  value={
                    row.days_until_critical === 0
                      ? "Ya crítico"
                      : row.days_until_critical != null
                        ? `${row.days_until_critical} d`
                        : "—"
                  }
                  explain="Días de calendario hasta autonomía bajo el umbral crítico en este escenario."
                  tone="border-amber-600/30 bg-amber-500/5"
                />
                <Kpi
                  label="Fecha crítica est."
                  value={fmtDate(row.critical_date)}
                  explain="Fecha estimada de cruce del umbral crítico (si la proyección lo alcanza)."
                />
                <Kpi
                  label="Fecha restricción est."
                  value={fmtDate(row.restriction_date)}
                  explain="Cuando la autonomía entraría en banda de alerta (&lt;60 d), orientativo."
                />
                <Kpi
                  label="Autonomía hoy"
                  value={fmt(row.days_autonomy_start, " d", 0)}
                  explain="Punto de partida con el embalse usable actual."
                />
                <Kpi
                  label={`Autonomía +${horizon} d`}
                  value={fmt(row.days_autonomy_end, " d", 0)}
                  explain="Colchón estimado al final del horizonte en este modo."
                  tone="border-violet-600/25 bg-violet-500/5"
                />
                <Kpi
                  label="Embalse fin"
                  value={fmt(row.stored_end_hm3, " hm³", 0)}
                  explain={`Desde ${fmt(row.stored_start_hm3, "", 0)} hm³ tras restar la demanda del escenario.`}
                />
              </div>

              {chart.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs text-muted dark:text-muted-dark">
                    Autonomía día a día: pronóstico (línea) vs seco / ET0 alta (área).
                  </p>
                  <div className="h-52 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} width={36} />
                        <Tooltip />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="dry"
                          name="Seco / ET0 alta"
                          stroke="#b45309"
                          fill="#f59e0b33"
                        />
                        <Line
                          type="monotone"
                          dataKey="baseline"
                          name="Pronóstico"
                          stroke="#7c3aed"
                          strokeWidth={2}
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : null}
            </>
          )}

          {(snap.caveats_es ?? []).length > 0 ? (
            <ul className="list-disc space-y-1 pl-4 text-[11px] leading-relaxed text-muted dark:text-muted-dark">
              {(snap.caveats_es ?? []).map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
