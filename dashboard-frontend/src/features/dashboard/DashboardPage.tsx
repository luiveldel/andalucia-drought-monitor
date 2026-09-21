import { useMemo, useState } from "react";
import { ReservoirEvolutionChart } from "@/components/charts/ReservoirEvolutionChart";
import { ClimateIndicatorsRow } from "@/components/climate/ClimateIndicatorsRow";
import { ExploitationSystemsPanel } from "@/components/climate/ExploitationSystemsPanel";
import { HeatStressPanel } from "@/components/climate/HeatStressPanel";
import { ClimateProvinceSelect } from "@/components/climate/ClimateProvinceSelect";
import { ClimateSubNav, type ClimateSubTab } from "@/components/climate/ClimateSubNav";
import { CLIMATE_REGIONAL, type ClimateProvince } from "@/constants/provinces";
import { buildClimateIndicators } from "@/services/dashboard/dashboard.service";
import { ForecastPanel } from "@/components/climate/ForecastPanel";
import { ObservedMeteoPanel } from "@/components/climate/ObservedMeteoPanel";
import { SiarObservedPanel } from "@/components/climate/SiarObservedPanel";
import { IrrigationAutonomyPanel } from "@/components/climate/IrrigationAutonomyPanel";
import { IrrigationAlertsPanel } from "@/components/climate/IrrigationAlertsPanel";
import { IrrigationProjectionPanel } from "@/components/climate/IrrigationProjectionPanel";
import { RiaSiarComparePanel } from "@/components/climate/RiaSiarComparePanel";
import { SiarWaterBalancePanel } from "@/components/climate/SiarWaterBalancePanel";
import { HeatDemandCrossPanel } from "@/components/climate/HeatDemandCrossPanel";
import { CutRiskPanel } from "@/components/climate/CutRiskPanel";
import { IrrigationScenariosPanel } from "@/components/climate/IrrigationScenariosPanel";
import { CropEtcPanel } from "@/components/climate/CropEtcPanel";
import { EffectivePrecipPanel } from "@/components/climate/EffectivePrecipPanel";
import { SpiPanel } from "@/components/climate/SpiPanel";
import { ProvinceCompare } from "@/components/compare/ProvinceCompare";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { DashboardMobileTabs } from "@/components/dashboard/DashboardTabs";
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
import { useT } from "@/i18n/useT";
import { useTabsStore } from "@/store/tabs.store";

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useDashboardQuery();
  const tab = useTabsStore((s) => s.tab);
  const t = useT();
  const [climateSub, setClimateSub] = useState<ClimateSubTab>("observed");
  const [climateProvince, setClimateProvince] = useState<ClimateProvince>(CLIMATE_REGIONAL);

  const climateIndicators = useMemo(() => {
    if (!data) return [];
    if (climateProvince === CLIMATE_REGIONAL) return data.climate;
    const bundle = data.climateByProvince?.[climateProvince];
    return bundle ? buildClimateIndicators(bundle) : data.climate;
  }, [climateProvince, data]);

  if (isLoading) {
    return (
      <DashboardShell>
        <DashboardHeader />
        <DashboardMobileTabs />
        <LoadingSkeleton />
      </DashboardShell>
    );
  }

  if (isError || !data) {
    return (
      <DashboardShell>
        <DashboardHeader />
        <DashboardMobileTabs />
        <EmptyState
          title={t("error.title")}
          message={error instanceof Error ? error.message : t("error.unknown")}
        />
        <Button type="button" className="mt-4" onClick={() => void refetch()}>
          {t("error.retry")}
        </Button>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell>
      <DashboardHeader updatedAt={data.updatedAt} />
      <DashboardMobileTabs />
      <main className="mt-6 space-y-10" role="tabpanel">
        {tab === "decision" ? (
          <DecisionCenter
            narrative={data.weeklyNarrative}
            deltas={data.weeklyDeltas}
            alerts={data.alerts}
            recommendations={data.recommendations}
            riskBoard={data.riskBoard}
            irrigationAutonomy={data.irrigationAutonomy}
          />
        ) : null}

        {tab === "overview" ? (
          <>
            <section>
              <SectionHeader title={t("section.kpis")} description={t("section.kpis.desc")} />
              <div className="mt-3">
                <KpiGrid kpis={data.kpis} />
              </div>
            </section>
            <section>
              <SectionHeader
                title="Semáforo provincial de riego"
                description="Autonomía usable (SiAR×Kc) por provincia. Cambia a llenado si quieres ver embalses."
              />
              <div className="mt-3">
                <ProvinceStatusMap provinces={data.provinces} defaultMode="irrigation" />
              </div>
            </section>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
              <div className="space-y-4 xl:col-span-2">
                <ReservoirEvolutionChart data={data.evolution} />
              </div>
              <div className="space-y-6">
                <SeverityDistributionCard items={data.severity} />
                <InsightsPanel insights={data.insights} />
              </div>
            </div>
            {data.dataNotes.length > 0 ? (
              <ul className="list-disc space-y-1 pl-4 text-xs text-muted dark:text-muted-dark">
                {data.dataNotes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}

        {tab === "map" ? (
          <section>
            <SectionHeader title={t("section.provinces")} description={t("section.provinces.desc")} />
            <div className="mt-3 space-y-4">
              <ProvinceStatusGrid provinces={data.provinces} />
              <ProvinceStatusMap provinces={data.provinces} defaultMode="irrigation" />
            </div>
          </section>
        ) : null}

        {tab === "climate" ? (
          <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <ClimateSubNav value={climateSub} onChange={setClimateSub} />
              <ClimateProvinceSelect value={climateProvince} onChange={setClimateProvince} />
            </div>
            {climateSub === "forecast" ? (
              <ForecastPanel forecast={data.meteoForecast} province={climateProvince} />
            ) : (
              <>
                <ObservedMeteoPanel meteo={data.meteoObserved} province={climateProvince} />
                <ClimateIndicatorsRow
                  indicators={climateIndicators}
                  scopeLabel={climateProvince}
                />
                <HeatStressPanel heatStress={data.heatStress} />
                <ExploitationSystemsPanel systems={data.exploitationSystems} />
                <SpiPanel spi={data.spi} />
              </>
            )}
          </div>
        ) : null}

        {tab === "irrigation" ? (
          <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <SectionHeader
                title={t("section.irrigation")}
                description={t("section.irrigation.desc")}
              />
              <ClimateProvinceSelect value={climateProvince} onChange={setClimateProvince} />
            </div>
            <IrrigationAlertsPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <IrrigationProjectionPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <SiarObservedPanel meteo={data.meteoSiar} province={climateProvince} />
            <SiarWaterBalancePanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <EffectivePrecipPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <HeatDemandCrossPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <CropEtcPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <IrrigationAutonomyPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
          </div>
        ) : null}

        {tab === "risk" ? (
          <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <SectionHeader
                title={t("section.risk")}
                description={t("section.risk.desc")}
              />
              <ClimateProvinceSelect value={climateProvince} onChange={setClimateProvince} />
            </div>
            <CutRiskPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
            <IrrigationScenariosPanel autonomy={data.irrigationAutonomy} province={climateProvince} />
          </div>
        ) : null}

        {tab === "compare" ? (
          <div className="space-y-6">
            <ProvinceCompare provinceNames={data.provinces.map((p) => p.province)} />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-end">
              <ClimateProvinceSelect value={climateProvince} onChange={setClimateProvince} />
            </div>
            <RiaSiarComparePanel autonomy={data.irrigationAutonomy} province={climateProvince} />
          </div>
        ) : null}

        {tab === "reservoirs" ? <ReservoirTable rows={data.reservoirs} /> : null}
      </main>
    </DashboardShell>
  );
}
