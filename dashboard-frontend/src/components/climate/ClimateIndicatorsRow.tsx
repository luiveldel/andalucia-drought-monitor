import { ClimateIndicatorCard } from "@/components/climate/ClimateIndicatorCard";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import type { ClimateIndicator } from "@/types/dashboard-model";

export function ClimateIndicatorsRow(props: { indicators: ClimateIndicator[] }) {
  return (
    <section>
      <SectionHeader title="Climate indicators" description="Compact signals for rainfall, temperature, SPI, and stress." />
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {props.indicators.map((c) => (
          <ClimateIndicatorCard key={c.id} indicator={c} />
        ))}
      </div>
    </section>
  );
}
