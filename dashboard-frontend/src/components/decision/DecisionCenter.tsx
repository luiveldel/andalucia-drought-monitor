import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { severityFillClass, severityLabel, severityRingClass } from "@/lib/severity";
import { cn } from "@/lib/utils";
import type {
  DecisionAlert,
  DecisionRecommendation,
  RiskBoardRow,
  WeeklyDeltas,
} from "@/types/dashboard-model";

function DeltaChip(props: { label: string; value: number; unit: string }) {
  const positive = props.value >= 0;
  return (
    <div className="rounded-lg border border-black/10 bg-surface px-3 py-2 dark:border-white/10 dark:bg-surface-dark">
      <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">{props.label}</p>
      <p
        className={cn(
          "mt-0.5 font-display text-lg font-semibold tabular-nums",
          positive ? "text-sev-normal" : "text-sev-critical",
        )}
      >
        {positive ? "+" : ""}
        {props.value}
        <span className="ml-1 text-xs font-medium text-muted dark:text-muted-dark">{props.unit}</span>
      </p>
    </div>
  );
}

export function DecisionCenter(props: {
  narrative: string;
  deltas: WeeklyDeltas;
  alerts: DecisionAlert[];
  recommendations: DecisionRecommendation[];
  riskBoard: RiskBoardRow[];
}) {
  const topRisk = [...props.riskBoard].sort((a, b) => b.risk_score - a.risk_score);
  return (
    <section className="space-y-4">
      <SectionHeader
        title="Centro de decisión"
        description="Qué está mal, dónde duele y qué conviene hacer esta semana."
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardContent className="pt-4">
            <p className="text-sm font-medium text-muted dark:text-muted-dark">Qué cambió esta semana</p>
            <p className="mt-2 text-base leading-relaxed text-ink dark:text-ink-dark">{props.narrative}</p>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <DeltaChip label="Llenado" value={props.deltas.fill_pct} unit="pp" />
              <DeltaChip label="Volumen" value={props.deltas.stored_hm3} unit="hm³" />
              <DeltaChip label="Precip. diaria" value={props.deltas.precip_mm} unit="mm" />
              <DeltaChip label="Déficit" value={props.deltas.deficit_mm} unit="mm" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm font-medium text-muted dark:text-muted-dark">Recomendaciones</p>
            <ul className="mt-3 space-y-3">
              {props.recommendations.map((r, i) => (
                <li key={i} className="rounded-lg border border-black/10 p-3 dark:border-white/10">
                  <p className="text-xs font-semibold uppercase tracking-wide text-terracotta dark:text-terracotta-dark">
                    {r.priority === "high" ? "Alta" : r.priority === "medium" ? "Media" : "Info"}
                  </p>
                  <p className="mt-1 text-sm font-semibold">{r.title}</p>
                  <p className="mt-1 text-sm text-muted dark:text-muted-dark">{r.detail}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm font-medium text-muted dark:text-muted-dark">Alertas accionables</p>
            {props.alerts.length === 0 ? (
              <p className="mt-3 text-sm text-muted dark:text-muted-dark">Sin alertas activas con los umbrales actuales.</p>
            ) : (
              <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1">
                {props.alerts.map((a) => (
                  <li
                    key={a.id}
                    className={cn(
                      "rounded-lg border px-3 py-2",
                      severityRingClass(a.severity),
                      severityFillClass(a.severity),
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold">{a.title}</p>
                      <span className="shrink-0 text-[11px] font-medium uppercase">{severityLabel[a.severity]}</span>
                    </div>
                    <p className="mt-1 text-sm opacity-90">{a.detail}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <p className="text-sm font-medium text-muted dark:text-muted-dark">Ranking de riesgo provincial</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[420px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">Provincia</th>
                    <th className="pb-2 font-medium">Riesgo</th>
                    <th className="pb-2 font-medium">Llenado</th>
                    <th className="pb-2 font-medium">Δ7d</th>
                  </tr>
                </thead>
                <tbody>
                  {topRisk.map((r) => (
                    <tr key={r.province} className="border-t border-black/5 dark:border-white/5">
                      <td className="py-2 font-medium">{r.province}</td>
                      <td className="py-2 tabular-nums">{r.risk_score}</td>
                      <td className="py-2 tabular-nums">{r.fill_pct}%</td>
                      <td
                        className={cn(
                          "py-2 tabular-nums",
                          r.trend_7d < 0 ? "text-sev-critical" : "text-sev-normal",
                        )}
                      >
                        {r.trend_7d > 0 ? "+" : ""}
                        {r.trend_7d} pp
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
