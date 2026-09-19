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
  spi?: SpiSnapshot;
}


export interface SpiProvinceRow {
  province_name: string;
  month_start?: string;
  spi_value: number | null;
  spi_class_es?: string;
  window_months?: number;
  calibration_months?: number;
  is_provisional?: boolean;
  method_tag?: string;
  precip_window_mm?: number;
}

export interface SpiSnapshot {
  available: boolean;
  provisional: boolean;
  caveat_es: string;
  as_of_month?: string;
  window_months?: number | null;
  calibration_months_max?: number | null;
  regional_spi?: number | null;
  provinces: SpiProvinceRow[];
}

export interface ProvinceCompareSide {
  province: string;
  found: boolean;
  observation_date?: string;
  fill_pct?: number;
  severity?: SeverityLevel;
  trend_7d?: number;
  stress?: number;
  deficit_mm?: number;
  precip_mm?: number;
  stored_hm3?: number;
  risk_score?: number;
  fill_sparkline?: Array<{ d: string; v: number }>;
  spi?: {
    spi_value: number | null;
    spi_class_es?: string;
    window_months?: number;
    calibration_months?: number;
    is_provisional?: boolean;
    month_start?: string;
  } | null;
}

export interface ProvinceCompareResponse {
  a: ProvinceCompareSide;
  b: ProvinceCompareSide;
  labels_es: Record<string, string>;
}
