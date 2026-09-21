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

export type IrrigationRiskLevel = "critical" | "warning" | "watch" | "ok" | "unknown";

export interface ProvinceStatus {
  province: string;
  fillPercentage: number;
  severity: SeverityLevel;
  trend?: number;
  /** Days of usable irrigation autonomy (SiAR×Kc). */
  irrigationDaysAutonomy?: number | null;
  irrigationRiskLevel?: IrrigationRiskLevel;
  daysUntilCritical?: number | null;
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
  irrigation_days_autonomy?: number | null;
  irrigation_risk_level?: "critical" | "warning" | "watch" | "ok" | "unknown" | string;
  days_until_critical?: number | null;
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
  irrigationAutonomy: IrrigationAutonomySnapshot;
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


export interface IrrigationAutonomyTrendPoint {
  date: string;
  days_autonomy: number | null;
  stored_hm3: number | null;
  daily_demand_hm3: number | null;
}



export interface IrrigationProjectionDay {
  date: string;
  et0_mm?: number | null;
  precip_mm?: number | null;
  daily_demand_hm3?: number | null;
  stored_hm3?: number | null;
  days_autonomy?: number | null;
}

export interface IrrigationProjectionProvince {
  province_name: string;
  available?: boolean;
  kc?: number | null;
  irrigated_ha?: number;
  stored_start_hm3?: number | null;
  stored_end_hm3?: number | null;
  cumulative_demand_hm3?: number | null;
  days_autonomy_start?: number | null;
  days_autonomy_end?: number | null;
  /** Calendar days until projected autonomy < threshold (0 = already critical). */
  days_until_critical?: number | null;
  critical_threshold_days?: number | null;
  risk_level_end?: string;
  days?: IrrigationProjectionDay[];
  error?: string;
}

export interface IrrigationProjectionSnapshot {
  available: boolean;
  horizon_days?: number;
  source?: string;
  attribution?: string;
  note?: string;
  regional?: IrrigationProjectionProvince | null;
  by_province?: IrrigationProjectionProvince[];
}

export interface RiaSiarCompareMetrics {
  stations?: number;
  et0_mm?: number | null;
  mean_temp_c?: number | null;
  precip_mm?: number | null;
  mean_humidity_pct?: number | null;
}

export interface RiaSiarCompareProvince {
  province_name: string;
  ria: RiaSiarCompareMetrics;
  siar: RiaSiarCompareMetrics;
  delta: {
    et0_mm?: number | null;
    mean_temp_c?: number | null;
    precip_mm?: number | null;
  };
}

export interface RiaSiarCompareSnapshot {
  available: boolean;
  as_of?: string | null;
  note?: string;
  regional?: RiaSiarCompareProvince | null;
  by_province?: RiaSiarCompareProvince[];
}

export interface IrrigationAutonomyAlert {
  code: string;
  severity: "critical" | "warning" | "watch";
  province_name: string;
  message_es: string;
}

export interface IrrigationAutonomyProvince {
  province_name: string;
  stored_hm3: number | null;
  stored_gross_hm3?: number | null;
  urban_excluded_hm3?: number | null;
  capacity_hm3: number | null;
  fill_pct: number | null;
  irrigated_ha: number;
  kc?: number | null;
  et0_mm: number | null;
  pe_mm: number | null;
  precip_mm: number | null;
  net_demand_mm: number | null;
  daily_demand_hm3: number | null;
  days_autonomy: number | null;
  days_autonomy_gross?: number | null;
  weeks_autonomy: number | null;
  risk_level: "critical" | "warning" | "watch" | "ok" | "unknown";
  siar_station_count: number;
  deficit_7d_hm3?: number | null;
  deficit_30d_hm3?: number | null;
  storage_burn_hm3_per_day?: number | null;
  burn_vs_demand_ratio?: number | null;
  autonomy_trend?: IrrigationAutonomyTrendPoint[];
  days_autonomy_delta_7d?: number | null;
  trend_direction?: "worsening" | "improving" | "stable" | "unknown";
}


export interface IrrigationThresholds {
  autonomy_critical_days?: number;
  autonomy_warning_days?: number;
  autonomy_watch_days?: number;
  drop_fast_7d?: number;
  drop_watch_7d?: number;
  burn_warning_ratio?: number;
  burn_critical_ratio?: number;
  until_critical_high_days?: number;
  until_critical_medium_days?: number;
}


export interface SiarWaterBalanceDay {
  date: string;
  et0_mm?: number | null;
  precip_mm?: number | null;
  pe_mm?: number | null;
  et0_minus_p_mm?: number | null;
  et0_minus_pe_mm?: number | null;
  station_count?: number;
}

export interface SiarWaterBalanceProvince {
  province_name: string;
  as_of?: string | null;
  et0_mm?: number | null;
  precip_mm?: number | null;
  pe_mm?: number | null;
  et0_minus_p_mm?: number | null;
  et0_minus_pe_mm?: number | null;
  balance_7d_mm?: number | null;
  balance_30d_mm?: number | null;
  balance_7d_pe_mm?: number | null;
  balance_30d_pe_mm?: number | null;
  days_in_7d?: number;
  days_in_30d?: number;
  band_7d?: "dry" | "moderate" | "mild" | "wet" | string;
  series?: SiarWaterBalanceDay[];
}

export interface SiarWaterBalanceSnapshot {
  available: boolean;
  as_of?: string | null;
  note?: string;
  unit?: string;
  definition_es?: string;
  regional?: SiarWaterBalanceProvince | null;
  by_province?: SiarWaterBalanceProvince[];
}


export interface HeatDemandCrossDay {
  date: string;
  province_name?: string;
  et0_mm?: number | null;
  precip_mm?: number | null;
  daily_demand_hm3?: number | null;
  tmax_c?: number | null;
  min_rh_pct?: number | null;
  stations_heat?: number;
  agri_risk?: number | null;
  is_heat_day?: boolean;
  heat_source?: string;
  peak_index?: number | null;
  irrigated_ha?: number;
  kc?: number | null;
  avg_tmax_c?: number | null;
  provinces_in_heat?: number;
}

export interface HeatDemandCrossProvince {
  province_name: string;
  days_total?: number;
  heat_days?: number;
  peak_days_count?: number;
  avg_demand_heat_hm3?: number | null;
  avg_demand_other_hm3?: number | null;
  avg_et0_heat_mm?: number | null;
  avg_et0_other_mm?: number | null;
  demand_lift_pct?: number | null;
  latest_date?: string | null;
  latest_is_heat?: boolean;
  latest_demand_hm3?: number | null;
  latest_tmax_c?: number | null;
  latest_peak_index?: number | null;
}

export interface HeatDemandCrossSnapshot {
  available: boolean;
  as_of_heat?: string | null;
  as_of_siar?: string | null;
  lookback_days?: number;
  note?: string;
  definition_es?: string;
  regional?: HeatDemandCrossProvince | null;
  by_province?: HeatDemandCrossProvince[];
  peak_days?: HeatDemandCrossDay[];
  series?: HeatDemandCrossDay[];
}

export interface IrrigationAutonomySnapshot {
  thresholds?: IrrigationThresholds;
  available: boolean;
  as_of_reservoir?: string | null;
  as_of_siar?: string | null;
  kc?: number | null;
  irrigated_ha_source?: string;
  storage_scope?: string;
  method_es?: string;
  note?: string;
  regional?: IrrigationAutonomyProvince | null;
  by_province?: IrrigationAutonomyProvince[];
  alerts?: IrrigationAutonomyAlert[];
  projection?: IrrigationProjectionSnapshot;
  ria_siar_compare?: RiaSiarCompareSnapshot;
  water_balance?: SiarWaterBalanceSnapshot;
  heat_demand_cross?: HeatDemandCrossSnapshot;
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


