import { ClimateIndicatorCard } from "@/components/climate/ClimateIndicatorCard";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { useT } from "@/i18n/useT";
import type { ClimateIndicator } from "@/types/dashboard-model";

export function ClimateIndicatorsRow(props: {
  indicators: ClimateIndicator[];
  scopeLabel?: string;
}) {
  const t = useT();
  const desc = props.scopeLabel
    ? `${t("section.climate.desc")} · ${props.scopeLabel}`
    : t("section.climate.desc");
  return (
    <section>
      <SectionHeader title={t("section.climate")} description={desc} />
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {props.indicators.map((c) => (
          <ClimateIndicatorCard key={c.id} indicator={c} />
        ))}
      </div>
    </section>
  );
}
