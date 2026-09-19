import type {
  ClimateIndicator,
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
    {
      id: "provinces",
      label: "Provincias en alerta",
      value: Number(api.provinces_in_alert ?? 0),
      unit: "de 8",
      severity: Number(api.provinces_in_alert ?? 0) >= 4 ? "emergency" : "warning",
    },
  ];
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

function buildEvolution(api: ApiPayload, range: DashboardTimeRange): ReservoirTimePoint[] {
  const series = api.basin_series ?? [];
  if (!series.length) {
    // fallback: regional fill sparkline as single "Andalucía" series
    return (api.sparkline_fill ?? []).map((r) => ({
      date: r.d,
      basin: "Andalucía",
      percentage: Number(r.v),
    }));
  }
  const points: ReservoirTimePoint[] = series.map((r) => ({
    date: String(r.hydrological_year),
    basin: r.basin_bucket,
    percentage: Number(r.avg_fill_pct),
  }));
  if (range === "12m") return points;
  // hydrological years are coarse; still return all for context
  return points;
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

function buildProvinces(api: ApiPayload): ProvinceStatus[] {
  const board = api.risk_board ?? [];
  if (board.length) {
    return board.map((r) => ({
      province: r.province,
      fillPercentage: Number(r.fill_pct),
      severity: r.severity ?? severityFromFill(Number(r.fill_pct)),
      trend: Number(r.trend_7d),
    }));
  }
  return (api.province_rows ?? []).map((p) => {
    const fill = Number(p.avg_fill_pct ?? p.fill_pct ?? 0);
    return {
      province: String(p.province_name ?? p.province ?? ""),
      fillPercentage: fill,
      severity: severityFromFill(fill),
    };
  });
}

function buildClimate(api: ApiPayload): ClimateIndicator[] {
  return [
    {
      id: "precip",
      label: "Lluvia acumulada (30d)",
      value: Number(api.precipitation_30d_mm ?? 0),
      unit: "mm",
      comparisonLabel: "Δ 7d precip diaria",
      comparisonValue: api.weekly_deltas?.precip_mm,
      series: (api.sparkline_precip ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "deficit",
      label: "Déficit hídrico (ET0 − precip)",
      value: Number(api.avg_water_deficit_mm ?? 0),
      unit: "mm/día",
      comparisonLabel: "Δ 7d",
      comparisonValue: api.weekly_deltas?.deficit_mm,
      series: (api.sparkline_deficit ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "stress",
      label: "Estrés hídrico",
      value: Number(api.avg_stress ?? 0),
      unit: "índice",
      series: (api.sparkline_stress ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
    {
      id: "fill",
      label: "Llenado medio",
      value: Number(api.avg_fill_pct ?? 0),
      unit: "%",
      comparisonLabel: "Δ 7d",
      comparisonValue: api.weekly_deltas?.fill_pct,
      series: (api.sparkline_fill ?? []).map((r) => ({ date: r.d, value: r.v })),
    },
  ];
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
  return insights.length ? insights : ["Sin insights — espera datos en marts."];
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
