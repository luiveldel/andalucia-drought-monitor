import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { IrrigationAutonomySnapshot, PesKpiSnapshot } from "@/types/dashboard-model";
import { useLocaleStore } from "@/store/locale.store";

const ESCENARIO_ORDER = ["Normalidad", "Prealerta", "Alerta", "Emergencia"] as const;

function escenarioTone(esc: string | null | undefined): string {
  switch (esc) {
    case "Emergencia":
      return "border-rose-600/40 bg-rose-500/15 text-rose-950 dark:text-rose-100";
    case "Alerta":
      return "border-amber-600/40 bg-amber-500/15 text-amber-950 dark:text-amber-100";
    case "Prealerta":
      return "border-yellow-600/35 bg-yellow-500/10 text-yellow-950 dark:text-yellow-100";
    case "Normalidad":
      return "border-emerald-600/35 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
    default:
      return "border-border/80 text-muted dark:text-muted-dark";
  }
}

function countTone(esc: string): string {
  switch (esc) {
    case "Emergencia":
      return "bg-rose-600 text-white";
    case "Alerta":
      return "bg-amber-500 text-ink";
    case "Prealerta":
      return "bg-yellow-400 text-ink";
    case "Normalidad":
      return "bg-emerald-600 text-white";
    default:
      return "bg-muted text-ink dark:bg-white/20 dark:text-ink-dark";
  }
}

export function PesEscasezKpiPanel(props: { autonomy: IrrigationAutonomySnapshot }) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const chg = props.autonomy.chg_layers;
  const kpi: PesKpiSnapshot | null | undefined = chg?.pes_kpi;
  const esc = kpi?.escasez;
  const seq = kpi?.sequia;

  if (!chg?.available && !kpi?.available) {
    return null;
  }

  const counts = esc?.counts_by_escenario ?? {};
  const worst = esc?.worst_escenario ?? null;
  const highlights = esc?.highlight_donana_huelva_sevilla ?? [];

  return (
    <section>
      <SectionHeader
        title={es ? "Escasez PES (CHG)" : "PES scarcity (CHG)"}
        description={
          es
            ? "Escenarios oficiales del Plan Especial de Sequías por UTE. Accionable para posibles cortes de riego. No es ICRA."
            : "Official Special Drought Plan scenarios by UTE. Actionable for irrigation cuts. Not ICRA."
        }
      />
      <Card className="mt-3 border-sky-700/20 dark:border-sky-400/25">
        <CardContent className="space-y-4 pt-4">
          {!kpi?.available || !esc?.available ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              {kpi?.error ||
                (es
                  ? "KPI PES aún no disponible (caché o GeoServer)."
                  : "PES KPI not available yet (cache or GeoServer).")}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-start gap-4">
                <div className={cn("min-w-[10rem] rounded-xl border p-3", escenarioTone(worst))}>
                  <p className="text-[11px] uppercase tracking-wide opacity-80">
                    {es ? "Peor escenario" : "Worst scenario"}
                  </p>
                  <p className="mt-1 font-display text-2xl font-semibold">
                    {worst || "—"}
                  </p>
                  <p className="mt-1 text-[11px] opacity-80">
                    {es ? "a fecha" : "as of"} {esc.as_of || kpi.as_of || "—"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {ESCENARIO_ORDER.map((label) => (
                    <div
                      key={label}
                      className="rounded-lg border border-border/70 px-3 py-2 text-center"
                    >
                      <p className="text-[10px] uppercase tracking-wide text-muted dark:text-muted-dark">
                        {label}
                      </p>
                      <p
                        className={cn(
                          "mt-1 inline-flex min-w-[2rem] justify-center rounded-full px-2 py-0.5 font-display text-lg font-semibold tabular-nums",
                          countTone(label),
                        )}
                      >
                        {counts[label] ?? 0}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-sm text-ink dark:text-ink-dark">
                {esc.headline_es ||
                  (es
                    ? `${esc.feature_count ?? 0} UTE con escenario PES`
                    : `${esc.feature_count ?? 0} UTEs with PES scenario`)}
              </p>

              {seq?.available ? (
                <p className="text-xs text-muted dark:text-muted-dark">
                  {seq.headline_es}
                  {seq.as_of ? ` · ${es ? "sequía a" : "drought as of"} ${seq.as_of}` : ""}
                </p>
              ) : null}

              {highlights.length > 0 ? (
                <div>
                  <p className="mb-1.5 text-xs font-medium text-ink dark:text-ink-dark">
                    {es
                      ? "Doñana / Huelva–Sevilla (nombre UTE)"
                      : "Doñana / Huelva–Seville (UTE name)"}
                  </p>
                  <ul className="flex flex-wrap gap-2 text-xs">
                    {highlights.map((h) => (
                      <li
                        key={h.cod_ute || h.nom_ute}
                        className={cn(
                          "rounded-full border px-2.5 py-1",
                          escenarioTone(h.escenario),
                        )}
                      >
                        {h.nom_ute || h.cod_ute}:{" "}
                        <span className="font-medium">{h.escenario}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <p className="text-[11px] leading-snug text-muted dark:text-muted-dark">
                {kpi.caveat_es || esc.caveat_es} · {kpi.attribution || chg?.attribution}
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
