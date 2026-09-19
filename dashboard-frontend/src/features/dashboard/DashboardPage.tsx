import { ReservoirEvolutionChart } from "@/components/charts/ReservoirEvolutionChart";
import { ClimateIndicatorsRow } from "@/components/climate/ClimateIndicatorsRow";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { KpiGrid } from "@/components/dashboard/KpiGrid";
import { LoadingSkeleton } from "@/components/dashboard/LoadingSkeleton";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { DecisionCenter } from "@/components/decision/DecisionCenter";
import { InsightsPanel } from "@/components/insights/InsightsPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ProvinceStatusMap } from "@/components/maps/ProvinceStatusMap";
import { ProvinceStatusGrid } from "@/components/provinces/ProvinceStatusGrid";
import { SeverityDistributionCard } from "@/components/severity/SeverityDistributionCard";
import { ReservoirTable } from "@/components/table/ReservoirTable";
import { Button } from "@/components/ui/button";
import { useDashboardQuery } from "@/hooks/useDashboardQuery";

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useDashboardQuery();

  if (isLoading) {
    return (
      <DashboardShell>
        <DashboardHeader />
        <LoadingSkeleton />
      </DashboardShell>
    );
  }

  if (isError || !data) {
    return (
      <DashboardShell>
        <DashboardHeader />
        <EmptyState
          title="No se pudo cargar el panel"
          message={error instanceof Error ? error.message : "Error desconocido"}
        />
        <Button type="button" className="mt-4" onClick={() => void refetch()}>
          Reintentar
        </Button>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell>
      <DashboardHeader updatedAt={data.updatedAt} />
      <main className="mt-8 space-y-10">
        <DecisionCenter
          narrative={data.weeklyNarrative}
          deltas={data.weeklyDeltas}
          alerts={data.alerts}
          recommendations={data.recommendations}
          riskBoard={data.riskBoard}
        />

        <section>
          <SectionHeader
            title="Indicadores clave"
            description="Valores del último día disponible en marts, con variación semanal."
          />
          <div className="mt-3">
            <KpiGrid kpis={data.kpis} />
          </div>
        </section>

        {/* Left column matches chart width; sidebar gets full stacked height for insights */}
        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <ReservoirEvolutionChart data={data.evolution} />
            <section>
              <SectionHeader
                title="Estado provincial"
                description="Ocho provincias andaluzas: llenado, severidad y tendencia."
              />
              <div className="mt-3">
                <ProvinceStatusGrid provinces={data.provinces} />
              </div>
            </section>
          </div>
          <aside className="flex min-h-0 flex-col gap-4 xl:sticky xl:top-4">
            <SeverityDistributionCard items={data.severity} />
            <InsightsPanel insights={data.insights} />
          </aside>
        </div>

        <section className="w-full">
          <ProvinceStatusMap provinces={data.provinces} />
        </section>

        <ClimateIndicatorsRow indicators={data.climate} />
        <ReservoirTable rows={data.reservoirs} />
        {data.dataNotes.length > 0 ? (
          <p className="text-xs text-muted dark:text-muted-dark">{data.dataNotes.join(" · ")}</p>
        ) : null}
      </main>
    </DashboardShell>
  );
}
