import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n/useT";
import { formatPct } from "@/lib/format";
import type { IrrigationRiskLevel, ProvinceStatus } from "@/types/dashboard-model";
import { cn } from "@/lib/utils";

function irrTone(level: IrrigationRiskLevel | undefined): string {
  switch (level) {
    case "critical":
      return "bg-rose-500/15 text-rose-800 dark:text-rose-200";
    case "warning":
      return "bg-amber-500/15 text-amber-900 dark:text-amber-100";
    case "watch":
      return "bg-sky-500/15 text-sky-900 dark:text-sky-100";
    case "ok":
      return "bg-emerald-500/15 text-emerald-900 dark:text-emerald-100";
    default:
      return "bg-muted/40 text-muted dark:text-muted-dark";
  }
}

function irrLabel(level: IrrigationRiskLevel | undefined): string {
  switch (level) {
    case "critical":
      return "Crítico";
    case "warning":
      return "Alerta";
    case "watch":
      return "Vigilancia";
    case "ok":
      return "Holgado";
    default:
      return "—";
  }
}

export function ProvinceStatusGrid(props: { provinces: ProvinceStatus[] }) {
  const t = useT();
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-4">
      {props.provinces.map((p) => (
        <Card key={p.province}>
          <CardContent className="p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-ink dark:text-ink-dark">{p.province}</span>
              <StatusBadge level={p.severity} />
            </div>
            <p className="mt-2 font-display text-2xl font-semibold tabular-nums text-ink dark:text-ink-dark">
              {formatPct(p.fillPercentage)}
            </p>
            {p.trend !== undefined ? (
              <p className="mt-1 text-xs tabular-nums text-muted dark:text-muted-dark">
                {t("province.trend7d")} {p.trend > 0 ? "+" : ""}
                {p.trend.toFixed(1)} p.p.
              </p>
            ) : null}
            {p.irrigationRiskLevel ? (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[11px] font-medium",
                    irrTone(p.irrigationRiskLevel),
                  )}
                  title="Semáforo autonomía de riego"
                >
                  Riego {irrLabel(p.irrigationRiskLevel)}
                  {p.irrigationDaysAutonomy != null
                    ? ` · ${Math.round(p.irrigationDaysAutonomy)} d`
                    : ""}
                </span>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
