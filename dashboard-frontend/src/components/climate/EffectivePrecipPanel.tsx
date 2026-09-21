import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  EffectivePrecipScope,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/store/locale.store";
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

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${(Number(n) * 100).toFixed(0)} %`;
}

function sourceLabel(src: string | undefined, es: boolean): string {
  switch (src) {
    case "siar_pepmon":
      return es ? "SiAR PePMon (oficial MAPA)" : "SiAR PePMon (MAPA)";
    case "estimacion_usda_scs":
      return es ? "Estimación USDA-SCS (no oficial)" : "USDA-SCS estimate (not official)";
    case "mixed":
      return es ? "Mixto (PePMon + estimación)" : "Mixed (PePMon + estimate)";
    default:
      return "—";
  }
}

function sourceClass(src: string | undefined): string {
  switch (src) {
    case "siar_pepmon":
      return "border-emerald-600/25 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
    case "estimacion_usda_scs":
      return "border-amber-600/30 bg-amber-500/10 text-amber-950 dark:text-amber-100";
    case "mixed":
      return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
    default:
      return "border-border bg-muted/30";
  }
}

function Kpi(props: { label: string; value: string; explain: string; tone?: string }) {
  return (
    <div className={cn("rounded-xl border p-3", props.tone ?? "border-border/80")}>
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
        {props.value}
      </p>
      <p className="mt-1.5 text-[11px] leading-snug text-muted dark:text-muted-dark">{props.explain}</p>
    </div>
  );
}

export function EffectivePrecipPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const snap = props.autonomy.effective_precip;
  const isRegional = props.province === CLIMATE_REGIONAL;
  const [showCaveats, setShowCaveats] = useState(false);

  const scope: EffectivePrecipScope | null | undefined = useMemo(() => {
    if (!snap?.available) return null;
    if (isRegional) return snap.regional;
    return (snap.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [snap, isRegional, props.province]);

  const chart = useMemo(
    () =>
      (scope?.series ?? []).map((d) => ({
        date: d.date.slice(5),
        precip: d.precip_mm ?? 0,
        pe: d.pe_mm ?? 0,
        lost: d.lost_mm ?? 0,
      })),
    [scope?.series],
  );

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={es ? "Precipitación efectiva (Pe)" : "Effective precipitation (Pe)"}
          description={
            snap?.note_es ||
            (es
              ? "Cuánta lluvia “entra” de verdad al suelo frente a la precipitación bruta. Aún sin datos SiAR."
              : "How much rain really reaches the soil vs gross precip. No SiAR data yet.")
          }
        />
      </section>
    );
  }

  const srcBadge = scope?.source_window_7d || scope?.source;

  return (
    <section>
      <SectionHeader
        title={es ? "Precipitación efectiva (Pe)" : "Effective precipitation (Pe)"}
        description={
          es
            ? "Lluvia bruta vs lo que suele quedar disponible para el suelo/regadío (PePMon SiAR; si falta, estimación clara)."
            : "Gross rain vs what typically reaches soil/irrigation (SiAR PePMon; clear estimate if missing)."
        }
      />
      <Card className="mt-3 border-sky-600/20 dark:border-sky-400/25">
        <CardContent className="space-y-4 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {es ? (
              <>
                La <strong className="text-ink dark:text-ink-dark">precipitación bruta</strong> es
                lo que midió el pluviómetro. La{" "}
                <strong className="text-ink dark:text-ink-dark">precipitación efectiva (Pe)</strong>{" "}
                es cuánto de esa lluvia suele quedar útil para el cultivo (menos escorrentía e
                intercepción). Preferimos el campo{" "}
                <strong className="text-ink dark:text-ink-dark">PePMon</strong> de SiAR/MAPA; solo
                si falta usamos una estimación USDA-SCS y la etiquetamos.
                {scope?.as_of ? ` · ${scope.province_name}: ${scope.as_of}` : ""}
              </>
            ) : (
              <>
                <strong className="text-ink dark:text-ink-dark">Gross precip</strong> is the gauge
                reading.{" "}
                <strong className="text-ink dark:text-ink-dark">Effective precip (Pe)</strong> is
                how much typically remains useful for the crop. We prefer SiAR/MAPA{" "}
                <strong className="text-ink dark:text-ink-dark">PePMon</strong>; only if missing we
                use a USDA-SCS estimate and label it.
                {scope?.as_of ? ` · ${scope.province_name}: ${scope.as_of}` : ""}
              </>
            )}
          </p>

          {!scope ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {es
                ? `Sin serie Pe para ${props.province}.`
                : `No Pe series for ${props.province}.`}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium",
                    sourceClass(srcBadge),
                  )}
                >
                  {sourceLabel(srcBadge, es)}
                </span>
                <span className="text-xs text-muted dark:text-muted-dark">
                  {es
                    ? `Ventana 7d · ${scope.days_in_7d ?? 7} días con dato`
                    : `7d window · ${scope.days_in_7d ?? 7} days with data`}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Kpi
                  label={es ? "Precip. bruta hoy" : "Gross precip today"}
                  value={fmt(scope.precip_mm, " mm", 2)}
                  explain={
                    es
                      ? "Lluvia medida hoy (media de estaciones SiAR de la provincia)."
                      : "Rain measured today (mean of provincial SiAR stations)."
                  }
                />
                <Kpi
                  label={es ? "Pe hoy" : "Pe today"}
                  value={fmt(scope.pe_mm ?? scope.effective_precip_mm, " mm", 2)}
                  explain={
                    es
                      ? "Lo que “entra” de verdad (PePMon o estimación etiquetada)."
                      : "What really enters (PePMon or labelled estimate)."
                  }
                  tone="border-sky-600/30 bg-sky-500/5"
                />
                <Kpi
                  label={es ? "Ratio Pe / P" : "Pe / P ratio"}
                  value={pct(scope.ratio_pe_over_p)}
                  explain={
                    es
                      ? "Porcentaje de la lluvia bruta que cuenta como efectiva hoy."
                      : "Share of gross rain counted as effective today."
                  }
                  tone="border-sky-600/30 bg-sky-500/5"
                />
                <Kpi
                  label={es ? "No efectiva hoy" : "Not effective today"}
                  value={fmt(scope.lost_mm, " mm", 2)}
                  explain={
                    es
                      ? "Diferencia bruta − Pe (escorrentía / intercepción aproximada)."
                      : "Gross − Pe (approx. runoff / interception)."
                  }
                />
                <Kpi
                  label={es ? "Suma 7 d · P / Pe" : "7d sum · P / Pe"}
                  value={`${fmt(scope.precip_7d_mm, "", 1)} / ${fmt(scope.pe_7d_mm, "", 1)}`}
                  explain={
                    es
                      ? `Acumulado semanal (mm). Ratio 7d: ${pct(scope.ratio_7d)}.`
                      : `Weekly totals (mm). 7d ratio: ${pct(scope.ratio_7d)}.`
                  }
                  tone="border-teal-600/25 bg-teal-500/5"
                />
                <Kpi
                  label={es ? "Suma 30 d · P / Pe" : "30d sum · P / Pe"}
                  value={`${fmt(scope.precip_30d_mm, "", 1)} / ${fmt(scope.pe_30d_mm, "", 1)}`}
                  explain={
                    es
                      ? `Acumulado mensual (mm). Ratio 30d: ${pct(scope.ratio_30d)}.`
                      : `Monthly totals (mm). 30d ratio: ${pct(scope.ratio_30d)}.`
                  }
                />
              </div>

              {chart.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs text-muted dark:text-muted-dark">
                    {es
                      ? "Barras = precip. bruta. Línea = Pe (efectiva)."
                      : "Bars = gross precip. Line = Pe (effective)."}
                  </p>
                  <div className="h-52 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={chart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border/60" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} width={36} />
                        <Tooltip />
                        <Bar dataKey="precip" name={es ? "P bruta" : "Gross P"} fill="#0284c7" opacity={0.45} />
                        <Line
                          type="monotone"
                          dataKey="pe"
                          name="Pe"
                          stroke="#0d9488"
                          strokeWidth={2}
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : null}

              {(snap.by_province?.length ?? 0) > 0 ? (
                <div className="overflow-x-auto">
                  <p className="mb-2 text-xs font-medium text-muted dark:text-muted-dark">
                    {es
                      ? "Ranking provincial · ratio Pe/P en 7 d (quién aprovecha mejor la lluvia reciente)"
                      : "Province ranking · 7d Pe/P ratio (who keeps more of recent rain)"}
                  </p>
                  <table className="w-full min-w-[480px] text-left text-sm">
                    <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                      <tr>
                        <th className="pb-2 font-medium">{es ? "Provincia" : "Province"}</th>
                        <th className="pb-2 font-medium">{es ? "P 7d" : "P 7d"}</th>
                        <th className="pb-2 font-medium">Pe 7d</th>
                        <th className="pb-2 font-medium">{es ? "Ratio 7d" : "7d ratio"}</th>
                        <th className="pb-2 font-medium">{es ? "Fuente" : "Source"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...(snap.by_province ?? [])]
                        .sort(
                          (a, b) =>
                            (b.ratio_7d ?? -1) - (a.ratio_7d ?? -1),
                        )
                        .map((p) => (
                          <tr
                            key={p.province_name}
                            className="border-t border-black/5 dark:border-white/5"
                          >
                            <td className="py-2 font-medium">{p.province_name}</td>
                            <td className="py-2 tabular-nums">{fmt(p.precip_7d_mm, "", 1)}</td>
                            <td className="py-2 tabular-nums font-semibold">
                              {fmt(p.pe_7d_mm, "", 1)}
                            </td>
                            <td className="py-2 tabular-nums">{pct(p.ratio_7d)}</td>
                            <td className="py-2">
                              <span
                                className={cn(
                                  "rounded-full border px-2 py-0.5 text-[11px] font-medium",
                                  sourceClass(p.source_window_7d || p.source),
                                )}
                              >
                                {sourceLabel(p.source_window_7d || p.source, es)}
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

          <div className="rounded-lg border border-dashed border-border/80 p-3">
            <button
              type="button"
              className="text-sm font-medium text-sky-800 underline-offset-2 hover:underline dark:text-sky-200"
              onClick={() => setShowCaveats((v) => !v)}
            >
              {showCaveats
                ? es
                  ? "Ocultar método y avisos"
                  : "Hide method & caveats"
                : es
                  ? "Ver método, limitaciones y avisos"
                  : "Show method, limits & caveats"}
            </button>
            {showCaveats ? (
              <div className="mt-3 space-y-2 text-[12px] leading-relaxed text-muted dark:text-muted-dark">
                {snap.formula_es ? (
                  <p>
                    <span className="font-medium text-ink dark:text-ink-dark">
                      {es ? "Fórmula: " : "Formula: "}
                    </span>
                    {snap.formula_es}
                  </p>
                ) : null}
                {snap.definition_es ? <p>{snap.definition_es}</p> : null}
                {(snap.caveats_es ?? []).length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5">
                    {(snap.caveats_es ?? []).map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                ) : null}
                {snap.note_es ? <p>{snap.note_es}</p> : null}
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
