import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import { cn } from "@/lib/utils";
import type { CutRiskScore, IrrigationAutonomySnapshot } from "@/types/dashboard-model";

function bandTone(band: string | undefined): string {
  switch (band) {
    case "critical":
      return "border-rose-600/35 bg-rose-500/10 text-rose-900 dark:text-rose-100";
    case "warning":
      return "border-amber-600/35 bg-amber-500/10 text-amber-950 dark:text-amber-100";
    case "watch":
      return "border-sky-600/30 bg-sky-500/10 text-sky-950 dark:text-sky-100";
    case "ok":
      return "border-emerald-600/30 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
    default:
      return "border-border/80 text-muted dark:text-muted-dark";
  }
}

function bandLabel(band: string | undefined): string {
  switch (band) {
    case "critical":
      return "Riesgo alto";
    case "warning":
      return "Planificar restricciones";
    case "watch":
      return "Vigilancia";
    case "ok":
      return "Cómodo";
    default:
      return "Sin dato";
  }
}

function ScoreHero(props: { row: CutRiskScore }) {
  const score = props.row.score;
  return (
    <div className={cn("rounded-xl border p-4", bandTone(props.row.band))}>
      <p className="text-[11px] uppercase tracking-wide opacity-80">Riesgo de corte</p>
      <p className="mt-1 font-display text-4xl font-semibold tabular-nums">
        {score == null ? "—" : Math.round(score)}
        <span className="ml-1 text-lg font-medium opacity-70">/100</span>
      </p>
      <p className="mt-1 text-sm font-medium">{bandLabel(props.row.band)}</p>
      {props.row.why_es ? (
        <p className="mt-2 text-[12px] leading-snug opacity-90">{props.row.why_es}</p>
      ) : null}
    </div>
  );
}

function Drivers(props: { row: CutRiskScore }) {
  const drivers = props.row.drivers ?? [];
  if (!drivers.length) return null;
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-ink dark:text-ink-dark">Por qué este número</p>
      <ul className="space-y-2">
        {drivers.map((d) => {
          const pct = Math.max(0, Math.min(100, Number(d.score ?? 0)));
          return (
            <li key={d.id} className="rounded-lg border border-border/70 p-2.5">
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="font-medium text-ink dark:text-ink-dark">{d.label_es}</span>
                <span className="tabular-nums text-muted dark:text-muted-dark">
                  {d.contribution?.toFixed(0) ?? "—"} pts
                  <span className="ml-1 text-[11px]">
                    (peso {(Number(d.weight) * 100).toFixed(0)}%)
                  </span>
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                <div
                  className="h-full rounded-full bg-terracotta/80 dark:bg-terracotta-dark/80"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] leading-snug text-muted dark:text-muted-dark">
                {d.explain_es}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function CutRiskPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const snap = props.autonomy.cut_risk;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: CutRiskScore | null | undefined = useMemo(() => {
    if (!snap?.available) return null;
    if (isRegional) return snap.regional ?? null;
    return (snap.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [isRegional, props.province, snap]);

  const table = useMemo(() => {
    const rows = [...(snap?.by_province ?? [])];
    rows.sort((a, b) => (Number(b.score ?? -1) - Number(a.score ?? -1)));
    return rows;
  }, [snap]);

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title="Riesgo de corte (0–100)"
          description={
            snap?.note_es ||
            "Combina llenado, autonomía, días hasta crítico, quemado SiAR y clima en un solo número accionable."
          }
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Riesgo de corte (0–100)"
        description="Un solo número para priorizar: más alto = más cerca de un posible corte de riego. Se explica solo y usa datos que ya tienes en Riego y Clima."
      />
      <Card className="mt-3 border-terracotta/25 dark:border-terracotta-dark/30">
        <CardContent className="space-y-5 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            Ámbito{" "}
            <span className="font-medium text-ink dark:text-ink-dark">{props.province}</span>
            {" · "}
            {snap.method_es}
          </p>
          {!row || !row.available ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin puntuación para {props.province}.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <ScoreHero row={row} />
              <Drivers row={row} />
            </div>
          )}

          {table.length > 0 ? (
            <div>
              <p className="mb-2 text-xs font-medium text-ink dark:text-ink-dark">
                Ranking provincial
              </p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border/80 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                      <th className="py-2 pr-2 font-medium">Provincia</th>
                      <th className="py-2 pr-2 font-medium">Riesgo</th>
                      <th className="py-2 pr-2 font-medium">Banda</th>
                      <th className="py-2 font-medium">Motor principal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.map((r) => {
                      const top = r.drivers?.[0];
                      return (
                        <tr
                          key={r.province_name}
                          className="border-b border-border/50 last:border-0"
                        >
                          <td className="py-2 pr-2 font-medium text-ink dark:text-ink-dark">
                            {r.province_name}
                          </td>
                          <td className="py-2 pr-2 tabular-nums font-semibold">
                            {r.score == null ? "—" : Math.round(r.score)}
                          </td>
                          <td className="py-2 pr-2">
                            <span
                              className={cn(
                                "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium",
                                bandTone(r.band),
                              )}
                            >
                              {bandLabel(r.band)}
                            </span>
                          </td>
                          <td className="py-2 text-muted dark:text-muted-dark">
                            {top ? `${top.label_es} (${top.contribution?.toFixed(0)} pts)` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {snap.note_es ? (
            <p className="text-[11px] leading-relaxed text-muted dark:text-muted-dark">
              {snap.note_es}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
