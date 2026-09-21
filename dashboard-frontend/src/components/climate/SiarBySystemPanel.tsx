import { useMemo, useState } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import type {
  IrrigationAutonomySnapshot,
  SiarBySystemRow,
} from "@/types/dashboard-model";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/store/locale.store";
import { useT } from "@/i18n/useT";

function fmt(n: number | null | undefined, digits = 1, unit = ""): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}${unit}`;
}

function riskTone(level: string | undefined): string {
  switch (level) {
    case "critical":
      return "text-sev-critical";
    case "warning":
      return "text-sev-emergency";
    case "watch":
      return "text-sev-alert";
    case "ok":
      return "text-sev-normal";
    default:
      return "text-muted dark:text-muted-dark";
  }
}

function riskLabel(level: string | undefined, es: boolean): string {
  const map: Record<string, [string, string]> = {
    critical: ["Crítico", "Critical"],
    warning: ["Alerta", "Warning"],
    watch: ["Vigilancia", "Watch"],
    ok: ["OK", "OK"],
    unknown: ["—", "—"],
  };
  const pair = map[level || "unknown"] || map.unknown;
  return es ? pair[0] : pair[1];
}

export function SiarBySystemPanel(props: { autonomy: IrrigationAutonomySnapshot }) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const t = useT();
  const snap = props.autonomy.siar_by_system;
  const [showCaveats, setShowCaveats] = useState(false);
  const [showShares, setShowShares] = useState(false);

  const rows: SiarBySystemRow[] = useMemo(
    () => [...(snap?.by_system ?? [])].slice(0, 20),
    [snap?.by_system],
  );

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={t("section.siar_by_system")}
          description={
            snap?.note_es ||
            (es
              ? "Demanda SiAR estimada por sistema de explotación. Aún sin datos."
              : "Estimated SiAR demand by exploitation system. No data yet.")
          }
        />
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <SectionHeader
        title={t("section.siar_by_system")}
        description={t("section.siar_by_system.desc")}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Embalse" : "Reservoir"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                {snap.as_of_reservoir ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">SiAR</p>
              <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                {snap.as_of_siar ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Sistemas" : "Systems"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums">{rows.length}</p>
            </div>
            <span className="rounded-full border border-amber-600/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-950 dark:text-amber-100">
              {es ? "Estimación (sin GIS)" : "Estimate (no GIS)"}
            </span>
          </div>

          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {snap.proxy_label_es ||
              (es
                ? "Repartimos la demanda SiAR de cada provincia entre sus sistemas según la cuota de capacidad de embalse (no urbano)."
                : "Provincial SiAR demand is shared across systems by non-urban reservoir capacity share.")}
          </p>

          {rows.length === 0 ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {es ? "Sin sistemas para mostrar." : "No systems to show."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">{es ? "Sistema" : "System"}</th>
                    <th className="pb-2 font-medium">{es ? "Demarcación" : "Basin"}</th>
                    <th className="pb-2 font-medium">{es ? "Provincias" : "Provinces"}</th>
                    <th className="pb-2 font-medium">{es ? "Demanda" : "Demand"}</th>
                    <th className="pb-2 font-medium">{es ? "Neto mm" : "Net mm"}</th>
                    <th className="pb-2 font-medium">{es ? "Almacenado" : "Stored"}</th>
                    <th className="pb-2 font-medium">{es ? "Autonomía" : "Autonomy"}</th>
                    <th className="pb-2 font-medium">{es ? "Riesgo" : "Risk"}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.exploitation_system}
                      className="border-t border-black/5 dark:border-white/5"
                    >
                      <td className="py-2 font-medium">
                        <div>{r.exploitation_system}</div>
                        <div className="text-[11px] text-muted dark:text-muted-dark">
                          {r.reservoir_count} {es ? "embalses" : "reservoirs"}
                          {r.irrigated_ha_est
                            ? ` · ~${r.irrigated_ha_est.toLocaleString()} ha`
                            : ""}
                        </div>
                      </td>
                      <td className="py-2 text-muted dark:text-muted-dark">
                        {r.watershed_demarcation}
                      </td>
                      <td className="py-2 text-xs text-muted dark:text-muted-dark">
                        {(r.provinces ?? []).join(", ") || "—"}
                      </td>
                      <td className="py-2 tabular-nums">
                        {fmt(r.daily_demand_hm3, 3)} hm³/d
                      </td>
                      <td className="py-2 tabular-nums">{fmt(r.net_demand_mm, 2)} mm</td>
                      <td className="py-2 tabular-nums">
                        {fmt(r.stored_hm3, 1)} / {fmt(r.capacity_hm3, 1)} hm³
                        <div className="text-[11px] text-muted dark:text-muted-dark">
                          {fmt(r.fill_pct, 1)}%
                        </div>
                      </td>
                      <td className="py-2 tabular-nums font-semibold">
                        {fmt(r.days_autonomy_est, 0)} {es ? "d" : "d"}
                      </td>
                      <td className={cn("py-2 font-semibold", riskTone(r.risk_level))}>
                        {riskLabel(r.risk_level, es)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-border/80 px-3 py-1.5 text-xs font-medium hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => setShowCaveats((v) => !v)}
            >
              {showCaveats
                ? es
                  ? "Ocultar matices"
                  : "Hide caveats"
                : es
                  ? "Ver matices"
                  : "Show caveats"}
            </button>
            <button
              type="button"
              className="rounded-lg border border-border/80 px-3 py-1.5 text-xs font-medium hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => setShowShares((v) => !v)}
            >
              {showShares
                ? es
                  ? "Ocultar cuotas provincia"
                  : "Hide province shares"
                : es
                  ? "Ver cuotas provincia→sistema"
                  : "Show province→system shares"}
            </button>
          </div>

          {showCaveats ? (
            <ul className="list-disc space-y-1 pl-5 text-xs leading-relaxed text-muted dark:text-muted-dark">
              {(snap.caveats_es ?? []).map((c) => (
                <li key={c}>{c}</li>
              ))}
              {snap.formula_es ? (
                <li className="font-mono text-[11px]">{snap.formula_es}</li>
              ) : null}
            </ul>
          ) : null}

          {showShares ? (
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full min-w-[560px] text-left text-xs">
                <thead className="bg-black/[0.03] text-[10px] uppercase text-muted dark:bg-white/[0.04] dark:text-muted-dark">
                  <tr>
                    <th className="px-3 py-2 font-medium">{es ? "Sistema" : "System"}</th>
                    <th className="px-3 py-2 font-medium">{es ? "Provincia" : "Province"}</th>
                    <th className="px-3 py-2 font-medium">{es ? "Cuota cap." : "Cap. share"}</th>
                    <th className="px-3 py-2 font-medium">{es ? "Demanda asignada" : "Allocated demand"}</th>
                    <th className="px-3 py-2 font-medium">ha≈</th>
                  </tr>
                </thead>
                <tbody>
                  {(snap.province_shares ?? []).slice(0, 80).map((s) => (
                    <tr
                      key={`${s.exploitation_system}-${s.province_name}`}
                      className="border-t border-black/5 dark:border-white/5"
                    >
                      <td className="px-3 py-1.5">{s.exploitation_system}</td>
                      <td className="px-3 py-1.5">{s.province_name}</td>
                      <td className="px-3 py-1.5 tabular-nums">
                        {s.capacity_share != null
                          ? `${(Number(s.capacity_share) * 100).toFixed(1)} %`
                          : "—"}
                      </td>
                      <td className="px-3 py-1.5 tabular-nums">
                        {fmt(s.allocated_demand_hm3_day, 4)} hm³/d
                      </td>
                      <td className="px-3 py-1.5 tabular-nums">
                        {s.allocated_irrigated_ha != null
                          ? Math.round(Number(s.allocated_irrigated_ha)).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
