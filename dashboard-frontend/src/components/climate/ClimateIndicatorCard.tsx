import { Card, CardContent } from "@/components/ui/card";
import type { ClimateIndicator } from "@/types/dashboard-model";
import { ResponsiveContainer, Area, AreaChart } from "recharts";

export function ClimateIndicatorCard(props: { indicator: ClimateIndicator }) {
  const { indicator } = props;
  const data = (indicator.series ?? []).map((p) => ({ ...p }));
  return (
    <Card className="min-h-[140px]">
      <CardContent className="p-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted dark:text-muted-dark">{indicator.label}</p>
        <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-ink dark:text-ink-dark">
          {indicator.value.toLocaleString("en-GB", { maximumFractionDigits: 2 })}
          {indicator.unit ? <span className="ml-1 text-sm font-medium text-muted">{indicator.unit}</span> : null}
        </p>
        {indicator.comparisonLabel !== undefined && indicator.comparisonValue !== undefined ? (
          <p className="mt-1 text-xs text-muted dark:text-muted-dark">
            {indicator.comparisonLabel}:{" "}
            <span className="font-medium tabular-nums text-ink dark:text-ink-dark">{indicator.comparisonValue}</span>
          </p>
        ) : null}
        {data.length > 1 ? (
          <div className="mt-2 h-12 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <Area type="monotone" dataKey="value" stroke="#1A6FA3" fill="#1A6FA333" strokeWidth={1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
