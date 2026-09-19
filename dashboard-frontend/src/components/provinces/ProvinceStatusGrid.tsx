import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n/useT";
import { formatPct } from "@/lib/format";
import type { ProvinceStatus } from "@/types/dashboard-model";

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
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
