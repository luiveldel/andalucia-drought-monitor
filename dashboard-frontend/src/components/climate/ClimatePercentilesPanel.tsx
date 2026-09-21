import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  ClimatePercentileMetric,
  ClimatePercentilesScope,
  ClimatePercentilesSnapshot,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/store/locale.store";
import { useT } from "@/i18n/useT";

function fmt(n: number | null | undefined, digits = 1, unit = ""): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function rankTone(rank: number | null | undefined): string {
  if (rank === null || rank === undefined || Number.isNaN(Number(rank))) {
    return "border-border bg-muted/30";
  }
  const r = Number(rank);
  if (r >= 80) return "border-rose-600/30 bg-rose-500/10 text-rose-900 dark:text-rose-100";
  if (r >= 60) return "border-amber-600/30 bg-amber-500/10 text-amber-950 dark:text-amber-100";
  if (r <= 20) return "border-emerald-600/25 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
  return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
}

function confLabel(c: string | undefined, es: boolean): string {
  switch (c) {
    case "ok":
      return es ? "confianza razonable" : "reasonable confidence";
    case "low":
      return es ? "historial corto" : "short history";
    case "very_low":
      return es ? "historial muy corto" : "very short history";
    default:
      return es ? "sin muestra" : "no sample";
  }
}

function MetricCard(props: {
  title: string;
  metric?: ClimatePercentileMetric;
  es: boolean;
  digits?: number;
}) {
  const m = props.metric;
  if (!m) return null;
  const digits = props.digits ?? 1;
  const unit = m.unit || "";
  return (
    <div className="rounded-xl border border-border/60 bg-muted/10 p-3 dark:bg-muted-dark/10">
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
        {props.title}
      </p>
      <div className="mt-1 flex flex-wrap items-baseline gap-3">
        <p className="font-display text-2xl font-semibold tabular-nums text-ink dark:text-ink-dark">
          {fmt(m.current, digits, unit ? ` ${unit}` : "")}
        </p>
        {m.percentile_rank !== null && m.percentile_rank !== undefined ? (
          <span
            className={cn(
              "rounded-full border px-2.5 py-0.5 text-xs font-medium tabular-nums",
              rankTone(m.percentile_rank),
            )}
          >
            P{Math.round(Number(m.percentile_rank))}
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-xs tabular-nums text-muted dark:text-muted-dark">
        {props.es ? "Media años disp." : "Mean avail. yrs"}: {fmt(m.mean_available, digits)}
        {" · "}
        P10 {fmt(m.p10, digits)} / P50 {fmt(m.p50, digits)} / P90 {fmt(m.p90, digits)}
      </p>
      <p className="mt-1 text-[11px] text-muted dark:text-muted-dark">
        {props.es ? "Años en muestra" : "Years in sample"}: {m.n_years ?? 0}
        {" · "}
        {confLabel(m.confidence, props.es)}
      </p>
    </div>
  );
}

export function ClimatePercentilesPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const t = useT();
  const snap: ClimatePercentilesSnapshot | undefined = props.autonomy.climate_percentiles;
  const [showCaveats, setShowCaveats] = useState(false);
  const isRegional = props.province === CLIMATE_REGIONAL;

  const scope: ClimatePercentilesScope | null | undefined = useMemo(() => {
    if (!snap?.available) return null;
    if (isRegional) return snap.regional;
    return (snap.by_province ?? []).find((p) => p.province_name === props.province) ?? snap.regional;
  }, [snap, isRegional, props.province]);

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={t("section.climate_percentiles")}
          description={
            snap?.note_es ||
            (es
              ? "Percentiles multi-año de ET0/demanda. Aún sin datos suficientes."
              : "Multi-year ET0/demand percentiles. Not enough data yet.")
          }
        />
      </section>
    );
  }

  const headline = es
    ? scope?.headline_es || snap.headline_es
    : scope?.headline_en || snap.headline_en || scope?.headline_es || snap.headline_es;
  const through = snap.through_doy?.label ?? "—";
  const coverageSiar = (snap.coverage?.siar_years ?? []).join(", ") || "—";
  const coverageRia = (snap.coverage?.ria_proxy_years ?? []).join(", ") || "—";
  const focusRank =
    scope?.campaign_to_date?.net_demand_mm_cum?.percentile_rank ??
    scope?.same_doy?.et0?.percentile_rank;

  return (
    <section className="space-y-3">
      <SectionHeader
        title={t("section.climate_percentiles")}
        description={t("section.climate_percentiles.desc")}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Día ref." : "Ref. day"}
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
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Confianza" : "Confidence"}
              </p>
              <p className="text-sm text-ink dark:text-ink-dark">
                {confLabel(snap.coverage?.confidence, es)}
              </p>
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
                rankTone(focusRank),
              )}
            >
              {headline}
            </p>
          ) : null}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink dark:text-ink-dark">
              {es ? `Mismo día del año (${through})` : `Same day of year (${through})`}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <MetricCard title="ET0" metric={scope?.same_doy?.et0} es={es} digits={1} />
              <MetricCard
                title={es ? "Demanda neta (Kc×max(0,ET0−Pe))" : "Net demand (Kc×max(0,ET0−Pe))"}
                metric={scope?.same_doy?.net_demand_mm}
                es={es}
                digits={1}
              />
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink dark:text-ink-dark">
              {es ? "Campaña abr → hoy (acumulado)" : "Campaign Apr → today (cumulative)"}
            </h3>
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricCard
                title={es ? "ET0 acum." : "Cum. ET0"}
                metric={scope?.campaign_to_date?.et0_cum}
                es={es}
                digits={0}
              />
              <MetricCard
                title={es ? "Demanda neta acum." : "Cum. net demand"}
                metric={scope?.campaign_to_date?.net_demand_mm_cum}
                es={es}
                digits={0}
              />
              <MetricCard
                title={es ? "Demanda acum. hm³" : "Cum. demand hm³"}
                metric={scope?.campaign_to_date?.demand_hm3_cum}
                es={es}
                digits={1}
              />
            </div>
          </div>

          {(scope?.same_doy?.et0?.samples?.length ?? 0) > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-border/60 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    <th className="py-2 pr-3 font-medium">{es ? "Año" : "Year"}</th>
                    <th className="py-2 pr-3 font-medium">ET0</th>
                    <th className="py-2 pr-3 font-medium">{es ? "Dem. neta" : "Net dem."}</th>
                    <th className="py-2 font-medium">{es ? "Fuente" : "Source"}</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {(scope?.same_doy?.et0?.samples ?? []).map((s) => {
                    const net = (scope?.same_doy?.net_demand_mm?.samples ?? []).find(
                      (x) => x.year === s.year,
                    );
                    return (
                      <tr
                        key={`${s.year}-${s.source}`}
                        className={cn(
                          "border-b border-border/40",
                          s.is_current ? "font-semibold" : "",
                        )}
                      >
                        <td className="py-2 pr-3">
                          {s.year}
                          {s.is_current ? (es ? " (actual)" : " (current)") : ""}
                        </td>
                        <td className="py-2 pr-3">{fmt(s.value, 1)}</td>
                        <td className="py-2 pr-3">{fmt(net?.value, 1)}</td>
                        <td className="py-2 text-xs uppercase text-muted dark:text-muted-dark">
                          {s.source === "siar" ? "SiAR" : s.source === "ria_proxy" ? "RIA" : s.source}
                          {s.doy_offset_days ? ` (±${s.doy_offset_days}d)` : ""}
                        </td>
                      </tr>
                    );
                  })}
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
              {snap.formula_es ? <li>{snap.formula_es}</li> : null}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
