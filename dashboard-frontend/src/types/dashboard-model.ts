export type SeverityLevel = "normal" | "warning" | "emergency" | "critical";

export interface DashboardKpi {
  id: string;
  label: string;
  value: number;
  unit: string;
  delta?: number;
  trend?: number[];
  severity?: SeverityLevel;
}

export interface ReservoirTimePoint {
  date: string;
  basin: string;
  percentage: number;
  volumeHm3?: number;
}

export interface SeverityDistributionItem {
  level: SeverityLevel;
  percentage: number;
  affectedAreaHa?: number;
}

export interface ProvinceStatus {
  province: string;
  fillPercentage: number;
  severity: SeverityLevel;
  trend?: number;
}

export interface ClimateIndicator {
  id: string;
  label: string;
  value: number;
  unit: string;
  comparisonLabel?: string;
  comparisonValue?: number;
  series?: Array<{
    date: string;
    value: number;
  }>;
}

export interface ReservoirRecord {
  id: string;
  reservoir: string;
  basin: string;
  province: string;
  capacityHm3: number;
  currentHm3: number;
  fillPercentage: number;
  weeklyChange: number;
  status: SeverityLevel;
}

export type DashboardTimeRange = "30d" | "90d" | "12m";

export type AlertSeverity = SeverityLevel;

export interface DecisionAlert {
  id: string;
  severity: AlertSeverity;
  province: string;
  title: string;
  detail: string;
  metric?: string;
  value?: number;
}

export interface DecisionRecommendation {
  priority: "high" | "medium" | "info";
  title: string;
  detail: string;
}

export interface RiskBoardRow {
  province: string;
  fill_pct: number;
  trend_7d: number;
  stress: number;
  deficit_mm: number;
  severity: SeverityLevel;
  risk_score: number;
}

export interface WeeklyDeltas {
  fill_pct: number;
  stored_hm3: number;
  precip_mm: number;
  deficit_mm: number;
}

export interface DashboardSnapshot {
  updatedAt: string;
  kpis: DashboardKpi[];
  evolution: ReservoirTimePoint[];
  severity: SeverityDistributionItem[];
  provinces: ProvinceStatus[];
  insights: string[];
  climate: ClimateIndicator[];
  reservoirs: ReservoirRecord[];
  weeklyNarrative: string;
  weeklyDeltas: WeeklyDeltas;
  alerts: DecisionAlert[];
  recommendations: DecisionRecommendation[];
  riskBoard: RiskBoardRow[];
  dataNotes: string[];
}
