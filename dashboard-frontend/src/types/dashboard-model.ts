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
  critical_date?: string | null;
  restriction_date?: string | null;
  fill_pct_start?: number | null;
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



export interface CutRiskDriver {
  id: string;
  label_es: string;
  score: number | null;
  weight: number;
  contribution: number | null;
  explain_es: string;
}

export interface CutRiskScore {
  available: boolean;
  province_name?: string;
  score: number | null;
  band?: "ok" | "watch" | "warning" | "critical" | "unknown" | string;
  weights_used?: Record<string, number>;
  drivers?: CutRiskDriver[];
  why_es?: string;
  bands?: Record<string, string>;
  inputs?: Record<string, number | null | undefined>;
}

export interface CutRiskSnapshot {
  available: boolean;
  note_es?: string;
  method_es?: string;
  weights_nominal?: Record<string, number>;
  bands?: Record<string, string>;
  regional?: CutRiskScore | null;
  by_province?: CutRiskScore[];
}

export interface IrrigationScenarioModeMeta {
  id: string;
  label_es: string;
  describe_es: string;
}

export interface IrrigationScenarioRun {
  available: boolean;
  horizon_days?: number;
  mode?: string;
  extrapolated_beyond_om?: boolean;
  regional?: IrrigationProjectionProvince | null;
  by_province?: IrrigationProjectionProvince[];
}

export interface IrrigationScenariosSnapshot {
  available: boolean;
  modes?: IrrigationScenarioModeMeta[];
  horizons?: number[];
  note_es?: string;
  caveats_es?: string[];
  attribution?: string;
  source?: string;
  by_mode?: Record<string, Record<string, IrrigationScenarioRun>>;
}


export interface CropEtcCropRow {
  crop_id: string;
  name_es: string;
  name_en?: string;
  kc?: number | null;
  etc_mm?: number | null;
  etc_net_mm?: number | null;
  etc_7d_est_mm?: number | null;
  demand_hm3_if_all_ha?: number | null;
  stock_proxy_mm?: number | null;
  cover_days_proxy?: number | null;
  vs_baseline_kc_ratio?: number | null;
  vs_baseline_demand_ratio?: number | null;
  burn_vs_crop_demand_ratio?: number | null;
  baseline_days_autonomy?: number | null;
  pressure?: string;
}

export interface CropEtcKcMeta {
  crop_id: string;
  name_es: string;
  name_en?: string;
  kc: number;
  source_es: string;
}

export interface CropEtcScope {
  province_name: string;
  et0_mm?: number | null;
  pe_mm?: number | null;
  irrigated_ha?: number;
  stored_hm3?: number | null;
  baseline_kc?: number | null;
  stock_proxy_mm?: number | null;
  crops?: CropEtcCropRow[];
}

export interface CropEtcSnapshot {
  available: boolean;
  as_of_siar?: string | null;
  formula_es?: string;
  note_es?: string;
  caveats_es?: string[];
  kc_table?: CropEtcKcMeta[];
  crops_meta?: CropEtcKcMeta[];
  regional?: CropEtcScope | null;
  by_province?: CropEtcScope[];
}


export interface EffectivePrecipDay {
  date: string;
  precip_mm?: number | null;
  pe_mm?: number | null;
  pe_pmon_mm?: number | null;
  pe_est_mm?: number | null;
  lost_mm?: number | null;
  ratio_pe_over_p?: number | null;
  source?: string;
  pe_station_count?: number | null;
  station_count?: number | null;
}

export interface EffectivePrecipScope {
  province_name: string;
  as_of?: string | null;
  precip_mm?: number | null;
  pe_mm?: number | null;
  pe_pmon_mm?: number | null;
  pe_est_mm?: number | null;
  effective_precip_mm?: number | null;
  lost_mm?: number | null;
  ratio_pe_over_p?: number | null;
  source?: string;
  source_window_7d?: string;
  precip_7d_mm?: number | null;
  pe_7d_mm?: number | null;
  ratio_7d?: number | null;
  precip_30d_mm?: number | null;
  pe_30d_mm?: number | null;
  ratio_30d?: number | null;
  days_in_7d?: number;
  days_in_30d?: number;
  pe_station_count?: number | null;
  station_count?: number | null;
  series?: EffectivePrecipDay[];
}

export interface EffectivePrecipSnapshot {
  available: boolean;
  as_of?: string | null;
  unit?: string;
  source_preferred?: string;
  formula_es?: string;
  note_es?: string;
  caveats_es?: string[];
  definition_es?: string;
  regional?: EffectivePrecipScope | null;
  by_province?: EffectivePrecipScope[];
}


export interface SiarBySystemProvinceShare {
  exploitation_system: string;
  province_name: string;
  capacity_share?: number | null;
  capacity_hm3?: number | null;
  stored_hm3?: number | null;
  reservoir_count?: number;
  allocated_demand_hm3_day?: number | null;
  allocated_irrigated_ha?: number | null;
  net_demand_mm?: number | null;
  et0_mm?: number | null;
  pe_mm?: number | null;
  kc?: number | null;
  siar_station_count?: number;
}

export interface SiarBySystemRow {
  exploitation_system: string;
  watershed_demarcation?: string;
  is_estimate?: boolean;
  provinces?: string[];
  province_count?: number;
  reservoir_count?: number;
  stored_hm3?: number | null;
  capacity_hm3?: number | null;
  fill_pct?: number | null;
  irrigated_ha_est?: number;
  daily_demand_hm3?: number | null;
  net_demand_mm?: number | null;
  et0_mm?: number | null;
  pe_mm?: number | null;
  kc_w?: number | null;
  siar_station_count?: number;
  days_autonomy_est?: number | null;
  risk_level?: string;
  deficit_7d_hm3?: number | null;
  deficit_30d_hm3?: number | null;
}

export interface SiarBySystemSnapshot {
  available: boolean;
  as_of_reservoir?: string | null;
  as_of_siar?: string | null;
  proxy?: string;
  proxy_label_es?: string;
  excluded_systems?: string[];
  unit_demand?: string;
  unit_depth?: string;
  formula_es?: string;
  note_es?: string;
  caveats_es?: string[];
  method_es?: string;
  by_system?: SiarBySystemRow[];
  province_shares?: SiarBySystemProvinceShare[];
}


export interface CampaignCompareYear {
  year: number;
  source?: string;
  source_label_es?: string;
  window_start?: string;
  window_end?: string;
  days_with_data?: number;
  days_siar?: number;
  days_ria?: number;
  is_current?: boolean;
  cum_demand_hm3?: number | null;
  cum_net_demand_mm?: number | null;
  cum_et0_mm?: number | null;
  cum_pe_mm?: number | null;
}

export interface CampaignCompareProvince {
  province_name: string;
  irrigated_ha?: number;
  kc?: number | null;
  days_with_data?: number;
  cum_et0_mm?: number | null;
  cum_pe_mm?: number | null;
  cum_net_demand_mm?: number | null;
  cum_demand_hm3?: number | null;
  year?: number;
  source?: string;
  series?: { year: number; cum_demand_hm3?: number | null }[];
}

export interface CampaignCompareComparison {
  vs_year: number;
  vs_source?: string;
  current_hm3?: number | null;
  vs_hm3?: number | null;
  delta_hm3?: number | null;
  delta_pct?: number | null;
  verdict?: "worse" | "better" | "similar" | "unknown" | string;
  plain_es?: string;
  plain_en?: string;
}

export interface CampaignCompareSnapshot {
  available: boolean;
  campaign?: {
    label_es?: string;
    start_month?: number;
    start_day?: number;
    end_month?: number;
    end_day?: number;
  };
  as_of?: string | null;
  through_doy?: { month?: number; day?: number; label?: string } | null;
  current_year?: number | null;
  unit_demand?: string;
  unit_depth?: string;
  formula_es?: string;
  note_es?: string;
  caveats_es?: string[];
  method_es?: string;
  coverage?: {
    siar_years?: number[];
    ria_proxy_years?: number[];
    siar_min_fecha?: string | null;
    siar_max_fecha?: string | null;
    ria_min_fecha?: string | null;
    ria_max_fecha?: string | null;
  };
  headline_es?: string;
  headline_en?: string;
  regional?: CampaignCompareProvince | null;
  by_province?: CampaignCompareProvince[];
  years?: CampaignCompareYear[];
  comparisons?: CampaignCompareComparison[];
}



export interface ClimatePercentileMetric {
  current?: number | null;
  mean_available?: number | null;
  p10?: number | null;
  p50?: number | null;
  p90?: number | null;
  percentile_rank?: number | null;
  n_years?: number;
  n_samples?: number;
  confidence?: "ok" | "low" | "very_low" | "none" | string;
  unit?: string;
  samples?: {
    year: number;
    value?: number | null;
    source?: string;
    date?: string | null;
    doy_offset_days?: number;
    is_current?: boolean;
    window_start?: string | null;
    window_end?: string | null;
    days_with_data?: number;
  }[];
  plain_es?: string;
  plain_en?: string;
}

export interface ClimatePercentilesScope {
  province_name: string;
  irrigated_ha?: number;
  kc?: number | null;
  source_current?: string | null;
  same_doy?: {
    date_label?: string;
    date_used?: string | null;
    doy_window_half_days?: number;
    et0?: ClimatePercentileMetric;
    net_demand_mm?: ClimatePercentileMetric;
  };
  campaign_to_date?: {
    window_label_es?: string;
    et0_cum?: ClimatePercentileMetric;
    net_demand_mm_cum?: ClimatePercentileMetric;
    demand_hm3_cum?: ClimatePercentileMetric;
  };
  headline_es?: string;
  headline_en?: string;
}

export interface ClimatePercentilesSnapshot {
  available: boolean;
  as_of?: string | null;
  current_year?: number | null;
  through_doy?: { month?: number; day?: number; label?: string } | null;
  unit_depth?: string;
  unit_demand?: string;
  formula_es?: string;
  note_es?: string;
  caveats_es?: string[];
  method_es?: string;
  coverage?: {
    siar_years?: number[];
    ria_proxy_years?: number[];
    siar_min_fecha?: string | null;
    siar_max_fecha?: string | null;
    ria_min_fecha?: string | null;
    ria_max_fecha?: string | null;
    n_years_total?: number;
    confidence?: string;
  };
  headline_es?: string;
  headline_en?: string;
  regional?: ClimatePercentilesScope | null;
  by_province?: ClimatePercentilesScope[];
}


export interface StationReservoirLink {
  station_code: string;
  station_name?: string;
  province_name?: string;
  lat?: number | null;
  lon?: number | null;
  is_estimate?: boolean;
  link_method?: "nearest_reservoir" | "province_dominant_system" | string | null;
  reservoir_code?: string | null;
  reservoir_name?: string | null;
  exploitation_system?: string | null;
  watershed_demarcation?: string | null;
  distance_km?: number | null;
}

export interface StationReservoirMarker {
  reservoir_code: string;
  reservoir_name?: string;
  province_name?: string;
  exploitation_system?: string;
  watershed_demarcation?: string;
  lat?: number | null;
  lon?: number | null;
  capacity_hm3?: number | null;
  linked_station_count?: number;
}

export interface StationReservoirSystemAgg {
  exploitation_system: string;
  station_count?: number;
  reservoir_count?: number;
  is_estimate?: boolean;
}

export interface StationReservoirLinksSnapshot {
  available: boolean;
  as_of_siar?: string | null;
  method?: string;
  method_es?: string;
  proxy_label_es?: string;
  max_link_distance_km?: number;
  excluded_systems?: string[];
  crs_reservoirs?: string;
  note_es?: string;
  caveats_es?: string[];
  stations?: StationReservoirLink[];
  reservoirs?: StationReservoirMarker[];
  by_system?: StationReservoirSystemAgg[];
  summary?: {
    station_count?: number;
    linked_nearest?: number;
    linked_province_fallback?: number;
    unlinked?: number;
    reservoir_count?: number;
    system_count?: number;
  };
}


export interface IntradayHeatHour {
  date?: string;
  time?: string;
  hour_label?: string;
  temp_c?: number | null;
  humidity_pct?: number | null;
  et0_mm?: number | null;
  radiation?: number | null;
  stations?: number | null;
  heat_stress?: boolean;
  elevated_heat?: boolean;
}

export interface IntradayHeatScope {
  province_name: string;
  location_label?: string;
  hours_total?: number;
  heat_hours?: number;
  elevated_hours?: number;
  temp_mean_c?: number | null;
  temp_peak_c?: number | null;
  peak_minus_mean_c?: number | null;
  et0_sum_mm?: number | null;
  radiation_mean?: number | null;
  by_day?: Array<{
    date: string;
    hours?: number;
    heat_hours?: number;
    elevated_hours?: number;
    temp_mean_c?: number | null;
    temp_peak_c?: number | null;
  }>;
  series?: IntradayHeatHour[];
  plain_es?: string;
  plain_en?: string;
}

export interface IntradayHeatSnapshot {
  available: boolean;
  source?: string;
  source_label_es?: string;
  attribution?: string;
  as_of?: string | null;
  days?: number;
  grain?: string;
  thresholds?: {
    heat_temp_c?: number;
    heat_rh_pct?: number;
    elevated_temp_c?: number;
  };
  definition_es?: string;
  note_es?: string;
  caveats_es?: string[];
  siar_ready?: boolean;
  siar_table?: string;
  headline_es?: string;
  headline_en?: string;
  regional?: IntradayHeatScope | null;
  by_province?: IntradayHeatScope[];
}


export interface ChgLayerWmsConfig {
  url: string;
  layers: string;
  format?: string;
  transparent?: boolean;
  version?: string;
  attribution?: string;
  uppercase?: boolean;
}

export interface ChgLayerMeta {
  id: string;
  type_name?: string;
  title_es?: string;
  title_en?: string;
  render?: "geojson" | "wms" | string;
  endpoint?: string;
  feature_count_hint?: number | null;
  enabled_default?: boolean;
  priority?: number;
  note_es?: string;
  wms?: ChgLayerWmsConfig | null;
  datos_gob_es?: string;
  available?: boolean;
  fetched_at?: string | null;
  error?: string | null;
}

export interface ChgLayersSnapshot {
  available: boolean;
  provider?: string;
  attribution?: string;
  attribution_html?: string;
  base_wfs?: string;
  base_wms?: string;
  crs_request?: string;
  crs_native_typical?: string;
  wfs_version?: string;
  cache_ttl_s?: number;
  simplify_tol_deg?: number;
  as_of?: string | null;
  fetched_at?: string | null;
  lazy?: boolean;
  note_es?: string;
  caveats_es?: string[];
  layers?: ChgLayerMeta[];
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
  cut_risk?: CutRiskSnapshot;
  scenarios?: IrrigationScenariosSnapshot;
  crop_etc?: CropEtcSnapshot;
  effective_precip?: EffectivePrecipSnapshot;
  siar_by_system?: SiarBySystemSnapshot;
  campaign_compare?: CampaignCompareSnapshot;
  climate_percentiles?: ClimatePercentilesSnapshot;
  intraday_heat?: IntradayHeatSnapshot;
  station_reservoir_links?: StationReservoirLinksSnapshot;
  chg_layers?: ChgLayersSnapshot;
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


