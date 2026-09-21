import { useMemo } from "react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import type {
  IrrigationAutonomySnapshot,
  RiaSiarCompareProvince,
} from "@/types/dashboard-model";

function fmt(n: number | null | undefined, unit = "", digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  const sign = n > 0 && unit === "" ? "" : "";
  return `${sign}${Number(n).toFixed(digits)}${unit}`;
}

function deltaFmt(n: number | null | undefined, unit: string, digits: number): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}${unit}`;
}

export function RiaSiarComparePanel(props: {
  autonomy: IrrigationAutonomySnapshot;
  province: ClimateProvince;
}) {
  const cmp = props.autonomy.ria_siar_compare;
  const isRegional = props.province === CLIMATE_REGIONAL;

  const row: RiaSiarCompareProvince | null | undefined = useMemo(() => {
    if (!cmp?.available) return null;
    if (isRegional) return cmp.regional;
    return (cmp.by_province ?? []).find((p) => p.province_name === props.province) ?? null;
  }, [cmp, isRegional, props.province]);

  if (!cmp?.available) {
    return (
      <section>
        <SectionHeader title="RIA vs SiAR" description="Compara el mismo día en dos redes: RIA (Andalucía) y SiAR (MAPA riego). Sirve para ver si ET0 o lluvia discrepan entre fuentes." />
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="RIA vs SiAR"
        description={`Compara el mismo día en RIA y SiAR · ${props.province} · ${cmp.as_of ?? "—"} · Δ = SiAR − RIA`}
      />
      <Card className="mt-3 border-teal-600/20 dark:border-teal-400/25">
        <CardContent className="space-y-3 pt-4">
          <p className="text-sm leading-relaxed text-muted dark:text-muted-dark">
            Dos redes midiendo el clima del mismo día. Si SiAR marca más ET0 que RIA (Δ positivo),
            la demanda de riego estimada con SiAR será más exigente. Las diferencias grandes
            invitan a mirar cobertura de estaciones, no a mezclar las series a ciegas.
          </p>
          {!row ? (
            <p className="text-sm text-muted dark:text-muted-dark">Sin datos cruzados para {props.province}.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-border/60 text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                    <th className="py-2 pr-3 font-medium">Variable</th>
                    <th className="py-2 pr-3 font-medium">RIA</th>
                    <th className="py-2 pr-3 font-medium">SiAR</th>
                    <th className="py-2 font-medium">Δ</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  <tr className="border-b border-border/40">
                    <td className="py-2 pr-3">ET0 (mm)</td>
                    <td className="py-2 pr-3">{fmt(row.ria.et0_mm, "", 2)}</td>
                    <td className="py-2 pr-3">{fmt(row.siar.et0_mm, "", 2)}</td>
                    <td className="py-2">{deltaFmt(row.delta.et0_mm, "", 2)}</td>
                  </tr>
                  <tr className="border-b border-border/40">
                    <td className="py-2 pr-3">T media (°C)</td>
                    <td className="py-2 pr-3">{fmt(row.ria.mean_temp_c, "", 1)}</td>
                    <td className="py-2 pr-3">{fmt(row.siar.mean_temp_c, "", 1)}</td>
                    <td className="py-2">{deltaFmt(row.delta.mean_temp_c, "", 1)}</td>
                  </tr>
                  <tr className="border-b border-border/40">
                    <td className="py-2 pr-3">Precip (mm)</td>
                    <td className="py-2 pr-3">{fmt(row.ria.precip_mm, "", 2)}</td>
                    <td className="py-2 pr-3">{fmt(row.siar.precip_mm, "", 2)}</td>
                    <td className="py-2">{deltaFmt(row.delta.precip_mm, "", 2)}</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3">Estaciones</td>
                    <td className="py-2 pr-3">{row.ria.stations ?? "—"}</td>
                    <td className="py-2 pr-3">{row.siar.stations ?? "—"}</td>
                    <td className="py-2">—</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          {cmp.note ? (
            <p className="text-[11px] leading-relaxed text-muted dark:text-muted-dark">{cmp.note}</p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
