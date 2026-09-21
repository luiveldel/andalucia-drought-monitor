import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  CampaignCompareSnapshot,
  CampaignCompareYear,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/store/locale.store";
import { useT } from "@/i18n/useT";

function fmt(n: number | null | undefined, digits = 1, unit = ""): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function deltaFmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

function verdictTone(v: string | undefined): string {
  switch (v) {
    case "worse":
      return "border-rose-600/30 bg-rose-500/10 text-rose-900 dark:text-rose-100";
    case "better":
      return "border-emerald-600/25 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
    case "similar":
      return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
    default:
      return "border-border bg-muted/30";
  }
}

function sourceLabel(source: string | undefined, es: boolean): string {
  if (source === "siar") return "SiAR";
  if (source === "ria_proxy") return es ? "RIA (proxy)" : "RIA (proxy)";
  return source || "—";
}

function YearBar(props: { year: CampaignCompareYear; maxHm3: number; es: boolean }) {
  const hm3 = Number(props.year.cum_demand_hm3 || 0);
  const pct = props.maxHm3 > 0 ? Math.min(100, (hm3 / props.maxHm3) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "font-display font-semibold tabular-nums",
              props.year.is_current ? "text-ink dark:text-ink-dark" : "text-muted dark:text-muted-dark",
            )}
          >
            {props.year.year}
            {props.year.is_current ? (props.es ? " (actual)" : " (current)") : ""}
          </span>
          <span className="rounded-full border border-border/60 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted dark:text-muted-dark">
            {sourceLabel(props.year.source, props.es)}
          </span>
        </div>
        <span className="tabular-nums text-ink dark:text-ink-dark">
          {fmt(props.year.cum_demand_hm3, 1, " hm³")}
          <span className="ml-2 text-muted dark:text-muted-dark">
            {fmt(props.year.cum_net_demand_mm, 0, " mm")}
          </span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted/40 dark:bg-muted-dark/30">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            props.year.is_current ? "bg-teal-600 dark:bg-teal-400" : "bg-teal-600/40 dark:bg-teal-400/40",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] text-muted dark:text-muted-dark">
        {props.year.window_start} → {props.year.window_end}
        {" · "}
        {props.year.days_with_data ?? "—"} {props.es ? "días con dato" : "days with data"}
      </p>
    </div>
  );
}

export function CampaignComparePanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const t = useT();
  const snap: CampaignCompareSnapshot | undefined = props.autonomy.campaign_compare;
  const [showCaveats, setShowCaveats] = useState(false);
  const isRegional = props.province === CLIMATE_REGIONAL;

  const years = useMemo(() => {
    if (!snap?.years?.length) return [] as CampaignCompareYear[];
    if (isRegional) return snap.years;
    const prov = (snap.by_province ?? []).find((p) => p.province_name === props.province);
    if (!prov?.series?.length) return snap.years;
    const byYear = new Map(prov.series.map((s) => [s.year, s.cum_demand_hm3]));
    return snap.years.map((y) => ({
      ...y,
      cum_demand_hm3: byYear.has(y.year) ? (byYear.get(y.year) ?? null) : y.cum_demand_hm3,
      cum_net_demand_mm: null,
    }));
  }, [snap, isRegional, props.province]);

  const maxHm3 = useMemo(
    () => Math.max(0, ...years.map((y) => Number(y.cum_demand_hm3 || 0))),
    [years],
  );

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={t("section.campaign_compare")}
          description={
            snap?.note_es ||
            (es
              ? "Comparativa interanual de la campaña abr–sep. Aún sin datos suficientes."
              : "Interannual Apr–Sep campaign compare. Not enough data yet.")
          }
        />
      </section>
    );
  }

  const headline = es ? snap.headline_es : snap.headline_en || snap.headline_es;
  const through = snap.through_doy?.label ?? "—";
  const coverageSiar = (snap.coverage?.siar_years ?? []).join(", ") || "—";
  const coverageRia = (snap.coverage?.ria_proxy_years ?? []).join(", ") || "—";
  const topVerdict = snap.comparisons?.[0]?.verdict;

  return (
    <section className="space-y-3">
      <SectionHeader
        title={t("section.campaign_compare")}
        description={t("section.campaign_compare.desc")}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Hasta" : "Through"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                {through}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Año actual" : "Current year"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums">
                {snap.current_year ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">SiAR</p>
              <p className="text-sm tabular-nums text-ink dark:text-ink-dark">{coverageSiar}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                RIA proxy
              </p>
              <p className="text-sm tabular-nums text-ink dark:text-ink-dark">{coverageRia}</p>
            </div>
            {!isRegional ? (
              <span className="rounded-full border border-teal-600/30 bg-teal-500/10 px-2.5 py-1 text-[11px] font-medium text-teal-950 dark:text-teal-100">
                {props.province}
              </span>
            ) : null}
          </div>

          {headline ? (
            <p
              className={cn(
                "rounded-xl border px-3 py-2 text-sm font-medium leading-relaxed",
                verdictTone(topVerdict),
              )}
            >
              {headline}
            </p>
          ) : null}

          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {es
              ? `Demanda acumulada (hm³) de la misma campaña agrícola (1 abr → ${through}). Δ positivo = más demanda que el año de referencia (vamos peor).`
              : `Cumulative demand (hm³) for the same agricultural campaign (1 Apr → ${through}). Positive Δ = higher demand than the reference year (we are worse).`}
          </p>

          {years.length === 0 ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {es ? "Sin años comparables aún." : "No comparable years yet."}
            </p>
          ) : (
            <div className="space-y-3">
              {years.map((y) => (
                <YearBar key={y.year} year={y} maxHm3={maxHm3} es={es} />
              ))}
            </div>
          )}

          {(snap.comparisons ?? []).length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-border/60 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    <th className="py-2 pr-3 font-medium">{es ? "Vs año" : "Vs year"}</th>
                    <th className="py-2 pr-3 font-medium">Δ%</th>
                    <th className="py-2 pr-3 font-medium">Δ hm³</th>
                    <th className="py-2 font-medium">{es ? "Lectura" : "Reading"}</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {(snap.comparisons ?? []).map((c) => (
                    <tr key={c.vs_year} className="border-b border-border/40">
                      <td className="py-2 pr-3">
                        {c.vs_year}
                        <span className="ml-2 text-[10px] uppercase text-muted dark:text-muted-dark">
                          {sourceLabel(c.vs_source, es)}
                        </span>
                      </td>
                      <td className="py-2 pr-3">{deltaFmt(c.delta_pct, 0)}</td>
                      <td className="py-2 pr-3">{fmt(c.delta_hm3, 1)}</td>
                      <td className="py-2">
                        <span
                          className={cn(
                            "inline-block rounded-full border px-2 py-0.5 text-[11px]",
                            verdictTone(c.verdict),
                          )}
                        >
                          {es ? c.plain_es : c.plain_en}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          <button
            type="button"
            className="text-xs text-teal-800 underline-offset-2 hover:underline dark:text-teal-200"
            onClick={() => setShowCaveats((v) => !v)}
          >
            {showCaveats
              ? es
                ? "Ocultar matices"
                : "Hide caveats"
              : es
                ? "Ver cobertura y matices"
                : "Show coverage & caveats"}
          </button>
          {showCaveats ? (
            <ul className="list-disc space-y-1 pl-5 text-[12px] leading-relaxed text-muted dark:text-muted-dark">
              {(snap.caveats_es ?? []).map((c) => (
                <li key={c}>{c}</li>
              ))}
              {snap.method_es ? <li>{snap.method_es}</li> : null}
              {snap.note_es ? <li>{snap.note_es}</li> : null}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
