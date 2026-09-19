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

export interface ClimateProvinceMetrics {
  avg_fill_pct?: number;
  avg_precipitation_mm?: number;
  avg_water_deficit_mm?: number;
  avg_stress?: number;
  precipitation_30d_mm?: number;
  sparkline_fill?: Array<{ d: string; v: number }>;
  sparkline_precip?: Array<{ d: string; v: number }>;
  sparkline_deficit?: Array<{ d: string; v: number }>;
  sparkline_stress?: Array<{ d: string; v: number }>;
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
  climateByProvince: Record<string, ClimateProvinceMetrics>;
  reservoirs: ReservoirRecord[];
  weeklyNarrative: string;
  weeklyDeltas: WeeklyDeltas;
  alerts: DecisionAlert[];
  recommendations: DecisionRecommendation[];
  riskBoard: RiskBoardRow[];
  dataNotes: string[];
  spi?: SpiSnapshot;
  heatStress: HeatStressSnapshot;
  exploitationSystems: ExploitationSystemsSnapshot;
  meteoObserved: MeteoObservedSnapshot;
  meteoSiar: MeteoSiarSnapshot;
  meteoForecast: MeteoForecastSnapshot;
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



export interface HeatStressProvinceRow {
  observation_date: string;
  province_name: string;
  stations_in_heat_stress: number;
  avg_max_temp_c: number;
  avg_min_humidity_pct?: number;
  reservoir_fill_pct?: number;
  daily_water_deficit_mm?: number;
  agricultural_risk_index: number;
}

export interface HeatStressDayRollup {
  observation_date: string;
  provinces_affected: number;
  stations_in_heat_stress: number;
  avg_max_temp_c: number;
  agricultural_risk_index: number;
}

export interface HeatStressSnapshot {
  available: boolean;
  as_of?: string | null;
  latest: HeatStressProvinceRow[];
  recent_days: HeatStressDayRollup[];
}

export interface ExploitationSystemRow {
  calendar_year: number;
  calendar_month: number;
  exploitation_system: string;
  watershed_demarcation: string;
  active_reservoirs: number;
  total_stored_hm3: number;
  total_capacity_hm3: number;
  system_fill_pct: number;
}

export interface ExploitationSystemsSnapshot {
  available: boolean;
  as_of?: string | null;
  systems: ExploitationSystemRow[];
}

export interface MeteoAlert {
  severity: "critical" | "warning" | "info";
  code: string;
  title_es: string;
  detail_es: string;
}

export interface MeteoObservedMetrics {
  province_name?: string;
  mean_temp_c?: number | null;
  max_temp_c?: number | null;
  min_temp_c?: number | null;
  feels_like_c?: number | null;
  mean_humidity_pct?: number | null;
  precip_mm?: number | null;
  mean_wind_speed?: number | null;
  mean_wind_direction_deg?: number | null;
  wind_dir_label?: string | null;
  solar_radiation?: number | null;
  et0_mm?: number | null;
  condition?: string;
  condition_label_es?: string;
  pressure_hpa?: number | null;
  precip_probability?: number | null;
  uv_index?: number | null;
}

export interface MeteoTrendDay {
  date: string;
  mean_temp_c: number;
  mean_humidity_pct: number;
  precip_mm: number;
}


export interface MeteoSiarMetrics {
  province_name?: string;
  station_count?: number;
  mean_temp_c?: number | null;
  max_temp_c?: number | null;
  min_temp_c?: number | null;
  mean_humidity_pct?: number | null;
  precip_mm?: number | null;
  mean_wind_speed?: number | null;
  mean_wind_direction_deg?: number | null;
  wind_dir_label?: string | null;
  solar_radiation?: number | null;
  et0_mm?: number | null;
  effective_precip_mm?: number | null;
}

export interface MeteoSiarTrendDay {
  date: string;
  mean_temp_c: number;
  mean_humidity_pct: number;
  precip_mm: number;
  et0_mm?: number;
}

export interface MeteoSiarSnapshot {
  available: boolean;
  as_of?: string | null;
  grain?: string;
  source?: string;
  attribution?: string;
  note?: string;
  station_count?: number;
  regional?: MeteoSiarMetrics | null;
  by_province?: MeteoSiarMetrics[];
  trend_days?: MeteoSiarTrendDay[];
}

export interface MeteoObservedSnapshot {
  available: boolean;
  as_of?: string | null;
  grain?: string;
  note?: string;
  regional?: MeteoObservedMetrics | null;
  by_province?: MeteoObservedMetrics[];
  trend_days?: MeteoTrendDay[];
  /** Last N observation days per province (same grain as trend_days). */
  trend_by_province?: Record<string, MeteoTrendDay[]>;
  alerts?: MeteoAlert[];
}

export interface MeteoForecastCurrent {
  temp_c?: number | null;
  feels_like_c?: number | null;
  humidity_pct?: number | null;
  precip_probability?: number | null;
  pressure_hpa?: number | null;
  pressure_source?: string | null;
  wind_speed?: number | null;
  wind_dir?: number | null;
  uv_index?: number | null;
  weather_code?: number | null;
  condition?: string;
  condition_label_es?: string;
  time?: string;
}

export interface MeteoForecastHour {
  time: string;
  temp_c?: number | null;
  humidity_pct?: number | null;
  precip_probability?: number | null;
  feels_like_c?: number | null;
  weather_code?: number | null;
  condition?: string;
  condition_label_es?: string;
}

export interface MeteoForecastDay {
  date: string;
  t_max?: number | null;
  t_min?: number | null;
  precip_sum?: number | null;
  precip_probability_max?: number | null;
  uv_index_max?: number | null;
  wind_speed_max?: number | null;
  weather_code?: number | null;
  condition?: string;
  condition_label_es?: string;
}

export interface MeteoForecastSnapshot {
  available: boolean;
  source?: string;
  attribution?: string;
  location_label?: string;
  latitude?: number;
  longitude?: number;
  generated_at?: string | null;
  error?: string | null;
  current?: MeteoForecastCurrent | null;
  hourly_today?: MeteoForecastHour[];
  daily?: MeteoForecastDay[];
  alerts?: MeteoAlert[];
}


