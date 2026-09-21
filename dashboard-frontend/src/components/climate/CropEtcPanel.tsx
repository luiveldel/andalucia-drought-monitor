import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  CropEtcCropRow,
  CropEtcScope,
  IrrigationAutonomySnapshot,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/store/locale.store";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function pressureLabel(p: string | undefined, es: boolean): string {
  switch (p) {
    case "high":
      return es ? "Alta presión" : "High pressure";
    case "medium":
      return es ? "Media" : "Medium";
    case "watch":
      return es ? "Vigilancia" : "Watch";
    case "low":
      return es ? "Holgada" : "Comfortable";
    default:
      return "—";
  }
}

function pressureClass(p: string | undefined): string {
  switch (p) {
    case "high":
      return "border-rose-600/30 bg-rose-500/10 text-rose-900 dark:text-rose-100";
    case "medium":
      return "border-amber-600/30 bg-amber-500/10 text-amber-950 dark:text-amber-100";
    case "watch":
      return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
    case "low":
      return "border-emerald-600/25 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
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

function CropCard(props: { row: CropEtcCropRow; es: boolean; et0: number | null | undefined }) {
  const name = props.es ? props.row.name_es : props.row.name_en || props.row.name_es;
  return (
    <div className="rounded-xl border border-border/80 bg-panel/40 p-3 dark:bg-panel-dark/40">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium text-ink dark:text-ink-dark">{name}</p>
          <p className="mt-0.5 text-[11px] text-muted dark:text-muted-dark">
            Kc {fmt(props.row.kc, "", 2)}
            {props.et0 != null ? ` · ET0 ${fmt(props.et0, " mm", 2)}` : ""}
          </p>
        </div>
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            pressureClass(props.row.pressure),
          )}
        >
          {pressureLabel(props.row.pressure, props.es)}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Kpi
          label="ETc día"
          value={fmt(props.row.etc_mm, " mm", 2)}
          explain={
            props.es
              ? "Agua que pediría el cultivo hoy: Kc × ET0 SiAR."
              : "Crop water need today: Kc × SiAR ET0."
          }
          tone="border-teal-600/25 bg-teal-500/5"
        />
        <Kpi
          label={props.es ? "ETc − lluvia" : "ETc − rain"}
          value={fmt(props.row.etc_net_mm, " mm", 2)}
          explain={
            props.es
              ? "Tras restar la lluvia efectiva del día (si hubo)."
              : "After subtracting effective rainfall for the day."
          }
        />
        <Kpi
          label={props.es ? "Cobertura proxy" : "Proxy cover"}
          value={fmt(props.row.cover_days_proxy, " d", 0)}
          explain={
            props.es
              ? "Días que duraría el embalse si se reparte entre todas las ha de regadío (estimación)."
              : "Days of reservoir stock if spread over all irrigated ha (estimate)."
          }
          tone="border-amber-600/25 bg-amber-500/5"
        />
        <Kpi
          label={props.es ? "vs demanda base" : "vs baseline"}
          value={
            props.row.vs_baseline_kc_ratio != null
              ? `${fmt(Number(props.row.vs_baseline_kc_ratio) * 100, "%", 0)}`
              : "—"
          }
          explain={
            props.es
              ? "Respecto al Kc provincial ya usado en autonomía (100 % = igual de sed)."
              : "Versus the provincial Kc used in autonomy (100% = same thirst)."
          }
        />
      </div>
      <p className="mt-2 text-[11px] leading-snug text-muted dark:text-muted-dark">
        {props.es ? (
          <>
            Si toda la provincia fuera este cultivo: ~
            {fmt(props.row.demand_hm3_if_all_ha, " hm³", 2)} al día. ETc 7d (lineal):{" "}
            {fmt(props.row.etc_7d_est_mm, " mm", 0)}.
            {props.row.burn_vs_crop_demand_ratio != null
              ? ` Burn embalse / esta demanda: ×${fmt(props.row.burn_vs_crop_demand_ratio, "", 2)}.`
              : ""}
          </>
        ) : (
          <>
            If the whole province were this crop: ~
            {fmt(props.row.demand_hm3_if_all_ha, " hm³", 2)}/day. 7d ETc (linear):{" "}
            {fmt(props.row.etc_7d_est_mm, " mm", 0)}.
            {props.row.burn_vs_crop_demand_ratio != null
              ? ` Reservoir burn / this demand: ×${fmt(props.row.burn_vs_crop_demand_ratio, "", 2)}.`
              : ""}
          </>
        )}
      </p>
    </div>
  );
}

export function CropEtcPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const snap = props.autonomy.crop_etc;
  const isRegional = props.province === CLIMATE_REGIONAL;
  const [showSources, setShowSources] = useState(false);

  const scope: CropEtcScope | null | undefined = useMemo(() => {
    if (!snap?.available) return null;
    if (isRegional) return snap.regional;
    return (snap.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [snap, isRegional, props.province]);

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={es ? "Necesidades por cultivo (ETc)" : "Crop water needs (ETc)"}
          description={
            snap?.note_es ||
            (es
              ? "ETc = Kc × ET0 SiAR para cultivos representativos. Aún sin datos."
              : "ETc = Kc × SiAR ET0 for representative crops. No data yet.")
          }
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title={es ? "Necesidades por cultivo (ETc)" : "Crop water needs (ETc)"}
        description={
          es
            ? "Cuánta agua pediría olivar, cítricos, hortícolas… según SiAR, y cómo encaja con el agua embalsada (estimación)."
            : "How much water olive, citrus, vegetables… would need per SiAR, vs stored water (estimate)."
        }
      />
      <Card className="mt-3 border-teal-600/20 dark:border-teal-400/25">
        <CardContent className="space-y-4 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {es ? (
              <>
                Fórmula: <strong className="text-ink dark:text-ink-dark">ETc = Kc × ET0</strong>{" "}
                (SiAR del día
                {snap.as_of_siar ? ` ${snap.as_of_siar}` : ""}). El Kc adapta la “sed del aire”
                al tipo de cultivo.{" "}
                <strong className="text-ink dark:text-ink-dark">No son dotaciones oficiales</strong>
                : comparamos con un <em>proxy</em> (volumen embalsado ÷ hectáreas de regadío) y con
                la demanda base de autonomía.
                {scope
                  ? ` · ${scope.province_name}: ET0 ${fmt(scope.et0_mm, " mm", 2)}, stock proxy ${fmt(scope.stock_proxy_mm, " mm", 0)}.`
                  : ""}
              </>
            ) : (
              <>
                Formula: <strong className="text-ink dark:text-ink-dark">ETc = Kc × ET0</strong>{" "}
                (SiAR day
                {snap.as_of_siar ? ` ${snap.as_of_siar}` : ""}). Kc scales air thirst to the crop.{" "}
                <strong className="text-ink dark:text-ink-dark">Not official quotas</strong>: we
                compare to a <em>proxy</em> (stored volume ÷ irrigated ha) and autonomy baseline
                demand.
                {scope
                  ? ` · ${scope.province_name}: ET0 ${fmt(scope.et0_mm, " mm", 2)}, stock proxy ${fmt(scope.stock_proxy_mm, " mm", 0)}.`
                  : ""}
              </>
            )}
          </p>

          {!scope ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {es
                ? `Sin ETc para ${props.province} en el día SiAR.`
                : `No ETc for ${props.province} on the SiAR day.`}
            </p>
          ) : (
            <div className="space-y-3">
              {(scope.crops ?? []).map((c) => (
                <CropCard key={c.crop_id} row={c} es={es} et0={scope.et0_mm} />
              ))}
            </div>
          )}

          <div className="rounded-lg border border-dashed border-border/80 p-3">
            <button
              type="button"
              className="text-sm font-medium text-teal-800 underline-offset-2 hover:underline dark:text-teal-200"
              onClick={() => setShowSources((v) => !v)}
            >
              {showSources
                ? es
                  ? "Ocultar fuentes de Kc y avisos"
                  : "Hide Kc sources & caveats"
                : es
                  ? "Ver fuentes de Kc (FAO-56 / SiAR) y avisos"
                  : "Show Kc sources (FAO-56 / SiAR) & caveats"}
            </button>
            {showSources ? (
              <div className="mt-3 space-y-3 text-[12px] leading-relaxed text-muted dark:text-muted-dark">
                <ul className="list-disc space-y-1 pl-5">
                  {(snap.kc_table ?? snap.crops_meta ?? []).map((c) => (
                    <li key={c.crop_id}>
                      <span className="font-medium text-ink dark:text-ink-dark">
                        {es ? c.name_es : c.name_en || c.name_es}
                      </span>
                      {` · Kc ${fmt(c.kc, "", 2)}. `}
                      {c.source_es}
                    </li>
                  ))}
                </ul>
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
