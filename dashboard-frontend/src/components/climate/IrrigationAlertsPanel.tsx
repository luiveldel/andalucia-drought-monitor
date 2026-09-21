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

function codeExplain(code: string): string {
  switch (code) {
    case "autonomy_critical":
      return "Quedan muy pocos días de riego con el embalse usable actual.";
    case "autonomy_warning":
      return "La autonomía ya está en zona de planificar restricciones.";
    case "autonomy_watch":
      return "Todavía hay colchón, pero conviene seguir la evolución semanal.";
    case "autonomy_drop_fast":
      return "En pocos días se ha perdido mucho colchón: el vaciado se está acelerando.";
    case "autonomy_drop":
      return "Señal temprana: la autonomía empeora semana a semana.";
    case "burn_above_demand":
      return "El embalse baja más de lo que explica la demanda SiAR (otros usos o trasvases).";
    case "until_critical_near":
      return "La proyección dice que el umbral crítico está muy cerca en el calendario.";
    case "until_critical_medium":
      return "En unas semanas la autonomía proyectada podría entrar en crítico.";
    default:
      return "Aviso operativo ligado al riesgo de corte de riego.";
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

  const th = props.autonomy.thresholds;

  return (
    <section>
      <SectionHeader
        title="Alertas tempranas de riego"
        description="Avisos cuando la autonomía es baja, cae rápido o el embalse se vacía más de lo esperado. Sirven para actuar antes del corte."
      />
      <Card className="mt-3 border-rose-600/15 dark:border-rose-400/20">
        <CardContent className="space-y-3 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            {th?.autonomy_critical_days != null
              ? `Miramos tres cosas: cuántos días de autonomía quedan (crítico <${th.autonomy_critical_days} d, alerta <${th.autonomy_warning_days} d, vigilancia <${th.autonomy_watch_days} d), si esa cifra cae en ~7 días (rápido ≤${Math.abs(Number(th.drop_fast_7d))} d), y si el vaciado real supera la demanda SiAR.`
              : "Miramos autonomía baja, caídas semanales y vaciado más rápido que la demanda SiAR."}
          </p>
          {alerts.length === 0 ? (
            <p className="text-sm text-muted dark:text-muted-dark">
              Sin alertas activas para el ámbito seleccionado: ningún umbral se ha cruzado.
            </p>
          ) : (
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li
                  key={`${a.code}-${a.province_name}`}
                  className={`rounded-lg border px-3 py-2 text-sm ${sevClass(a.severity)}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-block rounded-full bg-black/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide dark:bg-white/10">
                      {sevLabel(a.severity)} · {a.province_name}
                    </span>
                  </div>
                  <p className="mt-1 leading-snug">{a.message_es}</p>
                  <p className="mt-1 text-[11px] leading-snug opacity-80">{codeExplain(a.code)}</p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
