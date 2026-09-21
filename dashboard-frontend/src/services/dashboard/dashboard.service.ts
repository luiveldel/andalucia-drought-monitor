import type {
  ClimateIndicator,
  ClimateProvinceMetrics,
  DashboardKpi,
  DashboardSnapshot,
  DashboardTimeRange,
  DecisionAlert,
  DecisionRecommendation,
  ProvinceStatus,
  ReservoirRecord,
  ReservoirTimePoint,
  RiskBoardRow,
  SeverityDistributionItem,
  SeverityLevel,
  WeeklyDeltas,
  SpiSnapshot,
  HeatStressSnapshot,
  ExploitationSystemsSnapshot,
  MeteoObservedSnapshot,
  MeteoSiarSnapshot,
  IrrigationAutonomySnapshot,
  MeteoForecastSnapshot,
} from "@/types/dashboard-model";

type ApiPayload = {
  latest_date?: string;
  avg_fill_pct?: number;
  total_stored_hm3?: number;
  provinces_in_alert?: number;
  avg_water_deficit_mm?: number;
  avg_precipitation_mm?: number;
  avg_stress?: number;
  precipitation_30d_mm?: number;
  province_rows?: Array<Record<string, unknown>>;
  agricultural_severity?: Array<{ status: string; value: number }>;
  sparkline_fill?: Array<{ d: string; v: number }>;
  sparkline_precip?: Array<{ d: string; v: number }>;
  sparkline_deficit?: Array<{ d: string; v: number }>;
  sparkline_stress?: Array<{ d: string; v: number }>;
  basin_series?: Array<{
    hydrological_year: string | number;
    basin_bucket: string;
    avg_fill_pct: number;
  }>;
  reservoir_rows?: Array<Record<string, unknown>>;
  weekly_deltas?: WeeklyDeltas;
  weekly_narrative?: string;
  alerts?: DecisionAlert[];
  recommendations?: DecisionRecommendation[];
  risk_board?: RiskBoardRow[];
  data_notes?: string[];
  spi?: SpiSnapshot;
  heat_stress?: HeatStressSnapshot;
  exploitation_systems?: ExploitationSystemsSnapshot;
  meteo_observed?: MeteoObservedSnapshot;
  meteo_siar?: MeteoSiarSnapshot;
  irrigation_autonomy?: IrrigationAutonomySnapshot;
  climate_by_province?: Record<string, ClimateProvinceMetrics>;
  meteo_forecast?: MeteoForecastSnapshot;
};

function severityFromFill(fill: number): SeverityLevel {
  if (fill >= 70) return "normal";
  if (fill >= 50) return "warning";
  if (fill >= 30) return "emergency";
  return "critical";
}

function mapAgStatus(status: string): SeverityLevel {
  const s = status.toLowerCase();
  if (s.includes("crit")) return "critical";
  if (s.includes("emerg")) return "emergency";
  if (s.includes("alert") || s.includes("warn")) return "warning";
  return "normal";
}

function sparkValues(rows: Array<{ d: string; v: number }> | undefined): number[] {
  return (rows ?? []).map((r) => Number(r.v)).filter((n) => Number.isFinite(n));
}

function buildKpis(api: ApiPayload): DashboardKpi[] {
  const fill = Number(api.avg_fill_pct ?? 0);
  const deltas = api.weekly_deltas ?? { fill_pct: 0, stored_hm3: 0, precip_mm: 0, deficit_mm: 0 };
  const kpis: DashboardKpi[] = [
    {
      id: "fill",
      label: "Llenado medio embalses",
      value: fill,
      unit: "%",
      delta: deltas.fill_pct,
      trend: sparkValues(api.sparkline_fill),
      severity: severityFromFill(fill),
    },
    {
      id: "stored",
      label: "Volumen almacenado",
      value: Number(api.total_stored_hm3 ?? 0),
      unit: "hm³",
      delta: deltas.stored_hm3,
      trend: sparkValues(api.sparkline_fill).map((v) => v * 100),
      severity: severityFromFill(fill),
    },
    {
      id: "rain",
      label: "Precipitación 30 días",
      value: Number(api.precipitation_30d_mm ?? 0),
      unit: "mm",
      delta: deltas.precip_mm,
      trend: sparkValues(api.sparkline_precip),
      severity: Number(api.precipitation_30d_mm ?? 0) < 20 ? "warning" : "normal",
    },
    {
      id: "deficit",
      label: "Déficit hídrico diario",
      value: Number(api.avg_water_deficit_mm ?? 0),
      unit: "mm",
      delta: deltas.deficit_mm,
      trend: sparkValues(api.sparkline_deficit),
      severity: Number(api.avg_water_deficit_mm ?? 0) >= 4 ? "emergency" : "warning",
    },
    {
      id: "stress",
      label: "Índice de estrés hídrico",
      value: Number(api.avg_stress ?? 0),
      unit: "",
      trend: sparkValues(api.sparkline_stress),
      severity: Number(api.avg_stress ?? 0) >= 0.7 ? "emergency" : "warning",
    },
  ];

  const cut = api.irrigation_autonomy?.cut_risk?.regional;
  if (cut?.available && cut.score != null && Number.isFinite(Number(cut.score))) {
    const s = Number(cut.score);
    const sev: SeverityLevel =
      s >= 75 ? "critical" : s >= 50 ? "emergency" : s >= 25 ? "warning" : "normal";
    kpis.unshift({
      id: "cut_risk",
      label: "Riesgo de corte",
      value: s,
      unit: "/100",
      severity: sev,
    });
  }

  const spiVal = api.spi?.regional_spi;
  if (spiVal != null && Number.isFinite(spiVal)) {
    const sev: SeverityLevel =
      spiVal <= -1.5 ? "critical" : spiVal <= -1.0 ? "emergency" : spiVal < 0 ? "warning" : "normal";
    kpis.splice(3, 0, {
      id: "spi",
      label: "SPI provisional",
      value: spiVal,
      unit: api.spi?.provisional ? "prov." : "",
      severity: sev,
    });
  }
  return kpis;
}

function rangeDays(range: DashboardTimeRange): number {
  if (range === "30d") return 30;
  if (range === "90d") return 90;
  return 400;
}

function buildEvolution(api: ApiPayload, range: DashboardTimeRange): ReservoirTimePoint[] {
  // Prefer daily regional fill from embalses (sparkline_fill). basin_series is yearly
  // and only yields 1–2 points, which looks like a straight line.
  const daily = api.sparkline_fill ?? [];
  if (daily.length) {
    const latest = daily.reduce((max, r) => (r.d > max ? r.d : max), daily[0]?.d ?? "");
    const latestMs = Date.parse(latest);
    const minMs = Number.isFinite(latestMs) ? latestMs - rangeDays(range) * 86400000 : 0;
    return daily
      .filter((r) => {
        const t = Date.parse(r.d);
        return Number.isFinite(t) ? t >= minMs : true;
      })
      .map((r) => ({
        date: r.d,
        basin: "Andalucía",
        percentage: Number(r.v),
      }));
  }
  // Fallback: hydrological-year basin averages
  return (api.basin_series ?? []).map((r) => ({
    date: String(r.hydrological_year),
    basin: r.basin_bucket,
    percentage: Number(r.avg_fill_pct),
  }));
}

function buildSeverity(api: ApiPayload): SeverityDistributionItem[] {
  const rows = api.agricultural_severity ?? [];
  const total = rows.reduce((s, r) => s + Number(r.value || 0), 0) || 1;
  return rows.map((r) => ({
    level: mapAgStatus(r.status),
    percentage: Math.round((Number(r.value) / total) * 1000) / 10,
    affectedAreaHa: Number(r.value),
  }));
}

function normProv(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .trim();
}

function irrigationLookup(api: ApiPayload): Map<
  string,
  { days: number | null; risk: string; until: number | null }
> {
  const m = new Map<string, { days: number | null; risk: string; until: number | null }>();
  const ia = api.irrigation_autonomy;
  const projBy = new Map<string, number | null>();
  for (const row of ia?.projection?.by_province ?? []) {
    projBy.set(normProv(String(row.province_name ?? "")), row.days_until_critical ?? null);
  }
  for (const row of ia?.by_province ?? []) {
    const name = String(row.province_name ?? "");
    m.set(normProv(name), {
      days: row.days_autonomy ?? null,
      risk: String(row.risk_level ?? "unknown"),
      until: projBy.get(normProv(name)) ?? null,
    });
  }
  return m;
}

function buildProvinces(api: ApiPayload): ProvinceStatus[] {
  const irr = irrigationLookup(api);
  const enrich = (province: string, base: ProvinceStatus): ProvinceStatus => {
    const hit = irr.get(normProv(province));
    if (!hit) return base;
    return {
      ...base,
      irrigationDaysAutonomy: hit.days,
      irrigationRiskLevel: (hit.risk as ProvinceStatus["irrigationRiskLevel"]) || "unknown",
      daysUntilCritical: hit.until,
    };
  };
  const board = api.risk_board ?? [];
  if (board.length) {
    return board.map((r) =>
      enrich(r.province, {
        province: r.province,
        fillPercentage: Number(r.fill_pct),
        severity: r.severity ?? severityFromFill(Number(r.fill_pct)),
        trend: Number(r.trend_7d),
      }),
    );
  }
  return (api.province_rows ?? []).map((p) => {
    const fill = Number(p.avg_fill_pct ?? p.fill_pct ?? 0);
    const province = String(p.province_name ?? p.province ?? "");
    return enrich(province, {
      province,
      fillPercentage: fill,
      severity: severityFromFill(fill),
    });
  });
}

function buildClimate(api: ApiPayload): ClimateIndicator[] {
  return buildClimateIndicators(api);
}

function buildReservoirs(api: ApiPayload): ReservoirRecord[] {
  return (api.reservoir_rows ?? []).map((r, i) => {
    const fill = Number(r.fill_pct ?? 0);
    const weekly =
      typeof r.weekly_change === "number"
        ? Number(r.weekly_change)
        : Number(String(r.delta_7d ?? "0").replace("+", "")) || 0;
    return {
      id: String(i + 1),
      reservoir: String(r.reservoir_name ?? "—"),
      basin: String(r.basin ?? "—"),
      province: String(r.province ?? "—"),
      capacityHm3: Number(r.capacity_hm3 ?? 0),
      currentHm3: Number(r.current_hm3 ?? 0),
      fillPercentage: fill,
      weeklyChange: weekly,
      status: (r.status as SeverityLevel) || severityFromFill(fill),
    };
  });
}

function buildInsights(api: ApiPayload): string[] {
  const insights: string[] = [];
  if (api.weekly_narrative) insights.push(api.weekly_narrative);
  for (const a of (api.alerts ?? []).slice(0, 3)) {
    insights.push(`${a.title}: ${a.detail}`);
  }
  for (const note of api.data_notes ?? []) insights.push(note);
  return insights.length ? insights : ["Sin lectura rápida todavía — esperando datos del día."];
}

function mapApiToSnapshot(api: ApiPayload, range: DashboardTimeRange): DashboardSnapshot {
  const updatedAt = api.latest_date
    ? `${api.latest_date}T12:00:00.000Z`
    : new Date().toISOString();
  return {
    updatedAt,
    kpis: buildKpis(api),
    evolution: buildEvolution(api, range),
    severity: buildSeverity(api),
    provinces: buildProvinces(api),
    insights: buildInsights(api),
    climate: buildClimate(api),
    reservoirs: buildReservoirs(api),
    weeklyNarrative: api.weekly_narrative ?? "",
    weeklyDeltas: api.weekly_deltas ?? {
      fill_pct: 0,
      stored_hm3: 0,
      precip_mm: 0,
      deficit_mm: 0,
    },
    alerts: api.alerts ?? [],
    recommendations: api.recommendations ?? [],
    riskBoard: api.risk_board ?? [],
    dataNotes: api.data_notes ?? [],
    spi: api.spi,
    heatStress: api.heat_stress ?? {
      available: false,
      as_of: null,
      latest: [],
      recent_days: [],
    },
    exploitationSystems: api.exploitation_systems ?? {
      available: false,
      as_of: null,
      systems: [],
    },
    meteoObserved: api.meteo_observed ?? {
      available: false,
      as_of: null,
      grain: "daily",
      note: "",
      regional: null,
      by_province: [],
      trend_days: [],
      trend_by_province: {},
      alerts: [],
    },
    meteoSiar: api.meteo_siar ?? {
      available: false,
      as_of: null,
      grain: "daily",
      source: "SiAR",
      attribution: "https://servicio.mapa.gob.es/siarweb/",
      note: "",
      station_count: 0,
      regional: null,
      by_province: [],
      trend_days: [],
    },
    irrigationAutonomy: api.irrigation_autonomy ?? {
      available: false,
      as_of_reservoir: null,
      as_of_siar: null,
      kc: null,
      irrigated_ha_source: "",
      storage_scope: "",
      method_es: "",
      note: "",
      regional: null,
      by_province: [],
      alerts: [],
      thresholds: {},
      projection: { available: false, horizon_days: 7, source: "", attribution: "", note: "", regional: null, by_province: [] },
      ria_siar_compare: { available: false, as_of: null, note: "", regional: null, by_province: [] },
      water_balance: { available: false, as_of: null, note: "", unit: "mm", regional: null, by_province: [] },
      heat_demand_cross: { available: false, as_of_heat: null, as_of_siar: null, lookback_days: 30, note: "", regional: null, by_province: [], peak_days: [], series: [] },
      cut_risk: { available: false, note_es: "", method_es: "", weights_nominal: {}, bands: {}, regional: null, by_province: [] },
      scenarios: { available: false, modes: [], horizons: [7, 14, 21], note_es: "", caveats_es: [], by_mode: {} },
      crop_etc: { available: false, as_of_siar: null, formula_es: "ETc (mm) = Kc × ET0_SiAR", note_es: "", caveats_es: [], kc_table: [], crops_meta: [], regional: null, by_province: [] },
      effective_precip: { available: false, as_of: null, unit: "mm", source_preferred: "siar_pepmon", formula_es: "", note_es: "", caveats_es: [], definition_es: "", regional: null, by_province: [] },
      siar_by_system: { available: false, as_of_reservoir: null, as_of_siar: null, proxy: "capacity_share_within_province", proxy_label_es: "", excluded_systems: [], unit_demand: "hm3/day", unit_depth: "mm", formula_es: "", note_es: "", caveats_es: [], method_es: "", by_system: [], province_shares: [] },
      station_reservoir_links: { available: false, as_of_siar: null, method: "nearest_non_urban_reservoir_or_province_dominant_system", method_es: "", proxy_label_es: "", max_link_distance_km: 80, excluded_systems: [], crs_reservoirs: "EPSG:25830→WGS84", note_es: "", caveats_es: [], stations: [], reservoirs: [], by_system: [], summary: { station_count: 0, linked_nearest: 0, linked_province_fallback: 0, unlinked: 0, reservoir_count: 0, system_count: 0 } },
      campaign_compare: { available: false, campaign: { label_es: "Campaña agrícola abr–sep", start_month: 4, start_day: 1, end_month: 9, end_day: 30 }, as_of: null, through_doy: null, current_year: null, unit_demand: "hm3", unit_depth: "mm", formula_es: "", note_es: "", caveats_es: [], method_es: "", coverage: { siar_years: [], ria_proxy_years: [] }, headline_es: "", headline_en: "", regional: null, by_province: [], years: [], comparisons: [] },
      intraday_heat: { available: false, source: "none", source_label_es: "", attribution: "", as_of: null, days: 0, grain: "hourly", thresholds: { heat_temp_c: 35, heat_rh_pct: 30, elevated_temp_c: 32 }, definition_es: "", note_es: "", caveats_es: [], siar_ready: false, siar_table: "raw.raw_siar_clima_horario", headline_es: "", headline_en: "", regional: null, by_province: [] },
      climate_percentiles: { available: false, as_of: null, current_year: null, through_doy: null, unit_depth: "mm", unit_demand: "hm3", formula_es: "", note_es: "", caveats_es: [], method_es: "", coverage: { siar_years: [], ria_proxy_years: [], n_years_total: 0, confidence: "none" }, headline_es: "", headline_en: "", regional: null, by_province: [] },
      chg_layers: { available: false, provider: "CHG IDE-CHG GeoServer", attribution: "", attribution_html: "", base_wfs: "https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/ows", base_wms: "https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/wms", crs_request: "EPSG:4326", crs_native_typical: "EPSG:25830", wfs_version: "1.1.0", cache_ttl_s: 86400, simplify_tol_deg: 0.005, as_of: null, fetched_at: null, lazy: true, note_es: "", caveats_es: [], layers: [] },
    },
    climateByProvince: api.climate_by_province ?? {},
    meteoForecast: api.meteo_forecast ?? {
      available: false,
      source: "Open-Meteo",
      attribution: "https://open-meteo.com",
      location_label: "Andalucía (centroide)",
      current: null,
      hourly_today: [],
      daily: [],
      alerts: [],
    },
  };
}


export async function fetchDashboardSnapshot(
  range: DashboardTimeRange,
): Promise<DashboardSnapshot> {
  const res = await fetch("/api/dashboard");
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `API error ${res.status}`);
  }
  const api = (await res.json()) as ApiPayload;
  return mapApiToSnapshot(api, range);
}


/** Build climate indicator cards from regional dashboard KPIs or a province bundle. */
export function buildClimateIndicators(
  source:
    | {
        precipitation_30d_mm?: number;
        avg_water_deficit_mm?: number;
        avg_stress?: number;
        avg_fill_pct?: number;
        weekly_deltas?: { precip_mm?: number; deficit_mm?: number; fill_pct?: number };
        sparkline_precip?: Array<{ d: string; v: number }>;
        sparkline_deficit?: Array<{ d: string; v: number }>;
        sparkline_stress?: Array<{ d: string; v: number }>;
        sparkline_fill?: Array<{ d: string; v: number }>;
      }
    | ClimateProvinceMetrics,
): ClimateIndicator[] {
  const weekly = "weekly_deltas" in source ? source.weekly_deltas : undefined;
  return [
    {
      id: "precip",
      label: "Lluvia acumulada (30d)",
      value: Number(source.precipitation_30d_mm ?? 0),
      unit: "mm",
      comparisonLabel: weekly ? "Δ 7d precip diaria" : undefined,
      comparisonValue: weekly?.precip_mm,
      series: (source.sparkline_precip ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "deficit",
      label: "Déficit hídrico (ET0 − precip)",
      value: Number(source.avg_water_deficit_mm ?? 0),
      unit: "mm/día",
      comparisonLabel: weekly ? "Δ 7d" : undefined,
      comparisonValue: weekly?.deficit_mm,
      series: (source.sparkline_deficit ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "stress",
      label: "Estrés hídrico",
      value: Number(source.avg_stress ?? 0),
      unit: "índice",
      series: (source.sparkline_stress ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "fill",
      label: "Llenado medio",
      value: Number(source.avg_fill_pct ?? 0),
      unit: "%",
      comparisonLabel: weekly ? "Δ 7d" : undefined,
      comparisonValue: weekly?.fill_pct,
      series: (source.sparkline_fill ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
  ];
}


export async function fetchMeteoForecast(province?: string): Promise<MeteoForecastSnapshot> {
  const q =
    province && province !== "Andalucía"
      ? `?province=${encodeURIComponent(province)}`
      : "";
  const res = await fetch(`/api/meteo/forecast${q}`);
  if (!res.ok) {
    throw new Error(`Forecast HTTP ${res.status}`);
  }
  return (await res.json()) as MeteoForecastSnapshot;
}
