import { Card, CardContent } from "@/components/ui/card";
import { chartToneForId } from "@/lib/water-chart";
import type { ClimateIndicator } from "@/types/dashboard-model";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export function ClimateIndicatorCard(props: { indicator: ClimateIndicator }) {
  const { indicator } = props;
  const data = (indicator.series ?? []).map((p) => ({ ...p }));
  const gradId = `climate-area-${indicator.id}`;
  const tone = chartToneForId(indicator.id);

  return (
    <Card className="min-h-[140px]">
      <CardContent className="p-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
          {indicator.label}
        </p>
        <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-ink dark:text-ink-dark">
          {indicator.value.toLocaleString("en-GB", { maximumFractionDigits: 2 })}
          {indicator.unit ? (
            <span className="ml-1 text-sm font-medium text-muted">{indicator.unit}</span>
          ) : null}
        </p>
        {indicator.comparisonLabel !== undefined && indicator.comparisonValue !== undefined ? (
          <p className="mt-1 text-xs text-muted dark:text-muted-dark">
            {indicator.comparisonLabel}:{" "}
            <span className="font-medium tabular-nums text-ink dark:text-ink-dark">
              {indicator.comparisonValue}
            </span>
          </p>
        ) : null}
        {data.length > 1 ? (
          <div className="mt-2 h-12 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tone.fillTop} />
                    <stop offset="55%" stopColor={tone.fillMid} />
                    <stop offset="100%" stopColor={tone.fillBottom} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={tone.stroke}
                  strokeWidth={1.5}
                  fill={`url(#${gradId})`}
                  fillOpacity={1}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
