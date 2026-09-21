import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { SpiSnapshot } from "@/types/dashboard-model";

function spiTone(v: number | null | undefined) {
  if (v == null) return "text-muted dark:text-muted-dark";
  if (v <= -1.5) return "text-sev-critical";
  if (v <= -1.0) return "text-sev-emergency";
  if (v < 0) return "text-sev-alert";
  if (v < 1.0) return "text-ink dark:text-ink-dark";
  return "text-sev-normal";
}

function classLabel(c?: string) {
  if (!c) return "—";
  return c.replaceAll("_", " ");
}

export function SpiPanel(props: { spi?: SpiSnapshot }) {
  const spi = props.spi;
  if (!spi) return null;

  return (
    <section className="space-y-3">
      <SectionHeader
        title="SPI provisional (objetivo 12 meses)"
        description="Índice estandarizado de precipitación. Con series cortas se calcula la mejor ventana disponible y se marca como provisional."
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                SPI regional
              </p>
              <p className={cn("font-display text-3xl font-semibold tabular-nums", spiTone(spi.regional_spi))}>
                {spi.regional_spi != null ? spi.regional_spi.toFixed(2) : "—"}
              </p>
            </div>
            <div className="text-sm text-muted dark:text-muted-dark">
              <p>
                Ventana: {spi.window_months ?? "—"} mes(es) · Calibración máx.:{" "}
                {spi.calibration_months_max ?? "—"} mes(es)
              </p>
              {spi.as_of_month ? <p>Referencia: {spi.as_of_month}</p> : null}
            </div>
          </div>
          <p className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-ink dark:text-ink-dark">
            {spi.caveat_es}
          </p>
          {spi.available && spi.provinces.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="text-xs uppercase text-muted dark:text-muted-dark">
                  <tr>
                    <th className="pb-2 font-medium">Provincia</th>
                    <th className="pb-2 font-medium">SPI</th>
                    <th className="pb-2 font-medium">Clase</th>
                    <th className="pb-2 font-medium">Precip. ventana</th>
                    <th className="pb-2 font-medium">Ventana</th>
                  </tr>
                </thead>
                <tbody>
                  {spi.provinces.map((p) => (
                    <tr key={p.province_name} className="border-t border-black/5 dark:border-white/5">
                      <td className="py-2 font-medium">{p.province_name}</td>
                      <td className={cn("py-2 tabular-nums", spiTone(p.spi_value))}>
                        {p.spi_value != null ? p.spi_value.toFixed(2) : "—"}
                      </td>
                      <td className="py-2">{classLabel(p.spi_class_es)}</td>
                      <td className="py-2 tabular-nums">
                        {p.precip_window_mm != null ? `${p.precip_window_mm} mm` : "—"}
                      </td>
                      <td className="py-2 tabular-nums">{p.window_months ?? "—"} m</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted dark:text-muted-dark">
              El índice SPI aún no está disponible. Cuando haya historial de lluvia suficiente, aparecerá aquí.
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
