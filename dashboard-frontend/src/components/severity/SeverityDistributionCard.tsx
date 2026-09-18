import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { severityHex, severityLabel } from "@/lib/severity";
import type { SeverityDistributionItem } from "@/types/dashboard-model";

export function SeverityDistributionCard(props: { items: SeverityDistributionItem[] }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <SectionHeader title="Severity distribution" description="Share of monitored agricultural area by drought band." />
        <ul className="mt-2 space-y-3">
          {props.items.map((row) => (
            <li key={row.level} className="flex items-center gap-3">
              <StatusBadge level={row.level} className="w-24 shrink-0 justify-center" />
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, row.percentage)}%`,
                      backgroundColor: severityHex(row.level),
                      opacity: 0.85,
                    }}
                  />
                </div>
              </div>
              <span className="w-12 text-right text-sm font-semibold tabular-nums text-ink dark:text-ink-dark">
                {row.percentage}%
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[11px] text-muted dark:text-muted-dark">
          Bands: {props.items.map((i) => `${severityLabel[i.level]} ${i.percentage}%`).join(" · ")}
        </p>
      </CardContent>
    </Card>
  );
}
