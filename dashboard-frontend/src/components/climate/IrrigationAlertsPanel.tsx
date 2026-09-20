import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL } from "@/constants/provinces";
import type { IrrigationAutonomyAlert, IrrigationAutonomySnapshot } from "@/types/dashboard-model";

function sevClass(sev: string): string {
  switch (sev) {
    case "critical":
      return "border-rose-600/30 bg-rose-500/10 text-rose-900 dark:text-rose-100";
    case "warning":
      return "border-amber-600/30 bg-amber-500/10 text-amber-950 dark:text-amber-100";
    default:
      return "border-sky-600/25 bg-sky-500/10 text-sky-950 dark:text-sky-100";
  }
}

function sevLabel(sev: string): string {
  switch (sev) {
    case "critical":
      return "Crítico";
    case "warning":
      return "Alerta";
    default:
      return "Vigilancia";
  }
}

export function IrrigationAlertsPanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province?: string;
}) {
  const all = props.autonomy.alerts ?? [];
  const alerts: IrrigationAutonomyAlert[] =
    !props.province || props.province === CLIMATE_REGIONAL
      ? all
      : all.filter((a) => a.province_name === props.province);

  if (!props.autonomy.available) return null;

  return (
    <section>
      <SectionHeader
        title="Alertas tempranas de riego"
        description="Umbrales de autonomía, caída semanal y vaciado vs demanda SiAR (piloto)."
      />
      <Card className="mt-3 border-rose-600/15 dark:border-rose-400/20">
        <CardContent className="space-y-2 pt-4">
          {alerts.length === 0 ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin alertas activas para el ámbito seleccionado.
            </p>
          ) : (
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li
                  key={`${a.code}-${a.province_name}`}
                  className={`rounded-lg border px-3 py-2 text-sm ${sevClass(a.severity)}`}
                >
                  <span className="mr-2 inline-block rounded-full bg-black/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide dark:bg-white/10">
                    {sevLabel(a.severity)} · {a.province_name}
                  </span>
                  <span className="leading-snug">{a.message_es}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
