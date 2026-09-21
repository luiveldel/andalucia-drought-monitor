"use client";

import "leaflet/dist/leaflet.css";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import type {
  ChgLayersSnapshot,
  IrrigationAutonomySnapshot,
  OpenLayersSnapshot,
  StationReservoirLink,
  StationReservoirLinksSnapshot,
  StationReservoirMarker,
} from "@/types/dashboard-model";
import { useT } from "@/i18n/useT";
import { useLocaleStore } from "@/store/locale.store";
import { cn } from "@/lib/utils";
import { useEffect, useMemo, useState } from "react";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  WMSTileLayer,
} from "react-leaflet";
import type { FeatureCollection } from "geojson";

const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY as string | undefined)?.trim() || "";
const TILE_BASE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE = CARTO_KEY ? `${TILE_BASE}?key=${encodeURIComponent(CARTO_KEY)}` : TILE_BASE;
const ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO';
const CHG_ATTR =
  '&copy; <a href="https://www.chguadalquivir.es/" target="_blank" rel="noopener">CHG</a> IDE-CHG';
const REDIAM_ATTR =
  '&copy; <a href="https://www.juntadeandalucia.es/medioambiente/site/rediam" target="_blank" rel="noopener">REDIAM</a> / Junta de Andalucía';

type ChgGeoPayload = {
  available?: boolean;
  feature_collection?: FeatureCollection;
  error?: string | null;
  attribution?: string;
  fetched_at?: string | null;
  feature_count?: number;
  note_es?: string;
};

async function fetchChgGeojson(layerId: string): Promise<ChgGeoPayload | null> {
  try {
    const res = await fetch(`/api/gis/chg/${layerId}.geojson`);
    if (!res.ok) return null;
    return (await res.json()) as ChgGeoPayload;
  } catch {
    return null;
  }
}

/** Stable pastel palette keyed by exploitation system name. */
const SYSTEM_PALETTE = [
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ef4444",
  "#14b8a6",
  "#f97316",
  "#6366f1",
  "#84cc16",
  "#ec4899",
  "#06b6d4",
  "#a855f7",
];

function systemColor(name: string | null | undefined): string {
  const s = (name || "—").trim();
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return SYSTEM_PALETTE[h % SYSTEM_PALETTE.length];
}


function escenarioColor(esc: string | null | undefined): string {
  const s = (esc || "").toLowerCase();
  if (s.includes("emerg")) return "#e11d48";
  if (s.includes("alerta") && !s.includes("pre")) return "#f59e0b";
  if (s.includes("prealerta") || s.includes("pre-alerta")) return "#eab308";
  if (s.includes("normal")) return "#10b981";
  return "#94a3b8";
}

function estadoSequiaColor(estado: string | null | undefined): string {
  const s = (estado || "").toLowerCase();
  if (s.includes("prolong") || s.includes("sequ")) return "#dc2626";
  if (s.includes("ausen")) return "#34d399";
  return "#94a3b8";
}

function fmtKm(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(1)} km`;
}

function linkLabel(method: string | null | undefined, es: boolean): string {
  if (method === "nearest_reservoir") return es ? "Embalse más cercano" : "Nearest reservoir";
  if (method === "province_dominant_system")
    return es ? "Sistema dominante provincial" : "Province dominant system";
  return es ? "Sin enlace" : "Unlinked";
}

export function SiarReservoirMapPanel(props: { autonomy: IrrigationAutonomySnapshot }) {
  const locale = useLocaleStore((s) => s.locale);
  const es = locale !== "en";
  const t = useT();
  const snap: StationReservoirLinksSnapshot | undefined = props.autonomy.station_reservoir_links;
  const chg: ChgLayersSnapshot | undefined = props.autonomy.chg_layers;
  const openLayers: OpenLayersSnapshot | undefined = props.autonomy.open_layers;
  const [filterSystem, setFilterSystem] = useState<string>("");
  const [showCaveats, setShowCaveats] = useState(false);
  const [listOpen, setListOpen] = useState(false);
  const [showSistemas, setShowSistemas] = useState(true);
  const [showRecintos, setShowRecintos] = useState(false);
  const [showBalsas, setShowBalsas] = useState(false);
  const [showDotacionOlivar, setShowDotacionOlivar] = useState(true);
  const [showSobreexplotadas, setShowSobreexplotadas] = useState(false);
  const [showVulnerables, setShowVulnerables] = useState(false);
  // Doñana REDIAM: ON by default — highlighted for Huelva–Sevilla
  const [showDonana, setShowDonana] = useState(true);
  // PES + piezómetros: ON by default (escasez actionable; piezos near Doñana)
  const [showPesSequia, setShowPesSequia] = useState(true);
  const [showPesEscasez, setShowPesEscasez] = useState(true);
  const [showPiezometros, setShowPiezometros] = useState(true);
  const [filterPiezoProv, setFilterPiezoProv] = useState<string>("");
  const [sistemasFc, setSistemasFc] = useState<FeatureCollection | null>(null);
  const [balsasFc, setBalsasFc] = useState<FeatureCollection | null>(null);
  const [dotacionFc, setDotacionFc] = useState<FeatureCollection | null>(null);
  const [sobreFc, setSobreFc] = useState<FeatureCollection | null>(null);
  const [vulnFc, setVulnFc] = useState<FeatureCollection | null>(null);
  const [pesSequiaFc, setPesSequiaFc] = useState<FeatureCollection | null>(null);
  const [pesEscasezFc, setPesEscasezFc] = useState<FeatureCollection | null>(null);
  const [piezoFc, setPiezoFc] = useState<FeatureCollection | null>(null);
  const [chgStatus, setChgStatus] = useState<string>("");
  const [chgFetchedAt, setChgFetchedAt] = useState<string | null>(null);

  const donanaMeta = useMemo(
    () => (openLayers?.layers ?? []).find((l) => l.id === "donana_plan_regadios"),
    [openLayers],
  );
  const icraMeta = useMemo(
    () => (openLayers?.layers ?? []).find((l) => l.id === "icra_download"),
    [openLayers],
  );

  const chgWms = useMemo(() => {
    const rec = (chg?.layers ?? []).find((l) => l.id === "recintos_riego_pub");
    return rec?.wms ?? {
      url: chg?.base_wms || "https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/wms",
      layers: "ggiscloud_root:recintos_riego_pub",
      format: "image/png",
      transparent: true,
      version: "1.1.1",
      attribution: CHG_ATTR,
    };
  }, [chg]);

  const donanaWms = useMemo(() => {
    return donanaMeta?.wms ?? {
      url: "/api/gis/open/rediam/donana.wms",
      layers: "Ambito_plan,Zona_A,Corredor_ecologico",
      format: "image/png",
      transparent: true,
      version: "1.1.1",
      attribution: REDIAM_ATTR,
    };
  }, [donanaMeta]);

  useEffect(() => {
    if (!showSistemas) return;
    let alive = true;
    setChgStatus(es ? "Cargando sistemas CHG…" : "Loading CHG systems…");
    void (async () => {
      const payload = await fetchChgGeojson("sistemas_explotacion");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setSistemasFc(payload.feature_collection);
        setChgFetchedAt(payload.fetched_at ?? null);
        setChgStatus(
          es
            ? `Sistemas CHG: ${payload.feature_count ?? payload.feature_collection.features?.length ?? 0} (simplificados)`
            : `CHG systems: ${payload.feature_count ?? payload.feature_collection.features?.length ?? 0} (simplified)`,
        );
      } else {
        setChgStatus(
          payload?.error ||
            (es ? "No se pudieron cargar los sistemas CHG." : "Could not load CHG systems."),
        );
      }
    })();
    return () => {
      alive = false;
    };
  }, [showSistemas, es]);

  useEffect(() => {
    if (!showBalsas) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("balsas");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setBalsasFc(payload.feature_collection);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showBalsas]);

  useEffect(() => {
    if (!showDotacionOlivar) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("dotacion_olivar");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setDotacionFc(payload.feature_collection);
        setChgFetchedAt(payload.fetched_at ?? null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showDotacionOlivar]);

  useEffect(() => {
    if (!showSobreexplotadas) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("zonas_sobreexplotadas");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setSobreFc(payload.feature_collection);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showSobreexplotadas]);

  useEffect(() => {
    if (!showVulnerables) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("zonas_vulnerables");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setVulnFc(payload.feature_collection);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showVulnerables]);

  useEffect(() => {
    if (!showPesSequia) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("pes_estado_sequia");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setPesSequiaFc(payload.feature_collection);
        setChgFetchedAt(payload.fetched_at ?? null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showPesSequia]);

  useEffect(() => {
    if (!showPesEscasez) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("pes_estado_escasez");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setPesEscasezFc(payload.feature_collection);
        setChgFetchedAt(payload.fetched_at ?? null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showPesEscasez]);

  useEffect(() => {
    if (!showPiezometros) return;
    let alive = true;
    void (async () => {
      const payload = await fetchChgGeojson("piezometros");
      if (!alive) return;
      if (payload?.available && payload.feature_collection) {
        setPiezoFc(payload.feature_collection);
      }
    })();
    return () => {
      alive = false;
    };
  }, [showPiezometros]);

  const piezoMeta = useMemo(
    () => (chg?.layers ?? []).find((l) => l.id === "piezometros"),
    [chg],
  );

  const piezoFiltered = useMemo(() => {
    if (!piezoFc) return null;
    if (!filterPiezoProv) return piezoFc;
    const feats = (piezoFc.features ?? []).filter((f) => {
      const prov = String((f.properties as { nom_prov?: string } | null)?.nom_prov || "");
      return prov.toLowerCase() === filterPiezoProv.toLowerCase();
    });
    return { type: "FeatureCollection" as const, features: feats };
  }, [piezoFc, filterPiezoProv]);

  const systems = useMemo(() => {
    const names = new Set<string>();
    for (const s of snap?.stations ?? []) {
      if (s.exploitation_system) names.add(s.exploitation_system);
    }
    for (const r of snap?.reservoirs ?? []) {
      if (r.exploitation_system) names.add(r.exploitation_system);
    }
    return [...names].sort((a, b) => a.localeCompare(b, "es"));
  }, [snap]);

  const stations: StationReservoirLink[] = useMemo(() => {
    const rows = snap?.stations ?? [];
    if (!filterSystem) return rows;
    return rows.filter((s) => s.exploitation_system === filterSystem);
  }, [snap?.stations, filterSystem]);

  const reservoirs: StationReservoirMarker[] = useMemo(() => {
    const rows = snap?.reservoirs ?? [];
    if (!filterSystem) return rows;
    return rows.filter((r) => r.exploitation_system === filterSystem);
  }, [snap?.reservoirs, filterSystem]);

  const stationPts = stations.filter(
    (s) => s.lat != null && s.lon != null && Number.isFinite(Number(s.lat)) && Number.isFinite(Number(s.lon)),
  );
  const reservoirPts = reservoirs.filter(
    (r) => r.lat != null && r.lon != null && Number.isFinite(Number(r.lat)) && Number.isFinite(Number(r.lon)),
  );

  if (!snap?.available) {
    return (
      <section>
        <SectionHeader
          title={t("section.siar_reservoir_map")}
          description={
            snap?.note_es ||
            (es
              ? "Mapa estación SiAR × embalse / sistema. Aún sin datos."
              : "SiAR station × reservoir / system map. No data yet.")
          }
        />
      </section>
    );
  }

  const summary = snap.summary;

  return (
    <section className="space-y-3">
      <SectionHeader
        title={t("section.siar_reservoir_map")}
        description={t("section.siar_reservoir_map.desc")}
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-baseline gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">SiAR</p>
              <p className="font-display text-xl font-semibold tabular-nums text-ink dark:text-ink-dark">
                {snap.as_of_siar ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Estaciones" : "Stations"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums">
                {summary?.station_count ?? stations.length}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Embalses" : "Reservoirs"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums">
                {summary?.reservoir_count ?? reservoirs.length}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Vecino ≤" : "Nearest ≤"}
                {snap.max_link_distance_km ?? 80} km
              </p>
              <p className="font-display text-xl font-semibold tabular-nums text-sev-normal">
                {summary?.linked_nearest ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted dark:text-muted-dark">
                {es ? "Fallback provincial" : "Province fallback"}
              </p>
              <p className="font-display text-xl font-semibold tabular-nums text-sev-alert">
                {summary?.linked_province_fallback ?? "—"}
              </p>
            </div>
          </div>

          <p className="text-sm text-muted dark:text-muted-dark">
            {snap.proxy_label_es || snap.method_es}
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs text-muted dark:text-muted-dark">
              {es ? "Filtrar sistema" : "Filter system"}
              <select
                className="ml-2 rounded-md border border-black/10 bg-white px-2 py-1 text-sm dark:border-white/10 dark:bg-white/5"
                value={filterSystem}
                onChange={(e) => setFilterSystem(e.target.value)}
              >
                <option value="">{es ? "Todos" : "All"}</option>
                {systems.map((sys) => (
                  <option key={sys} value={sys}>
                    {sys}
                  </option>
                ))}
              </select>
            </label>
            <span className="text-xs text-muted dark:text-muted-dark">
              ● {es ? "Estación SiAR" : "SiAR station"} · ■ {es ? "Embalse" : "Reservoir"}
            </span>
          </div>

          {chg?.available !== false || openLayers?.available !== false ? (
            <div className="space-y-3 rounded-md border border-black/10 bg-black/[0.02] p-3 dark:border-white/10 dark:bg-white/[0.03]">
              {/* Doñana first-class — Huelva / Sevilla */}
              {openLayers?.available !== false && donanaMeta ? (
                <div className="space-y-1.5 rounded border border-emerald-700/20 bg-emerald-700/[0.06] p-2 dark:border-emerald-400/20 dark:bg-emerald-400/[0.08]">
                  <p className="text-xs font-medium text-ink dark:text-ink-dark">
                    {es ? "Doñana (Huelva–Sevilla) · REDIAM" : "Doñana (Huelva–Seville) · REDIAM"}
                  </p>
                  <label className="inline-flex items-center gap-1.5 text-xs text-muted dark:text-muted-dark">
                    <input
                      type="checkbox"
                      checked={showDonana}
                      onChange={(e) => setShowDonana(e.target.checked)}
                    />
                    {es ? "Plan regadíos Doñana" : "Doñana irrigation plan"}
                  </label>
                  <p className="text-[11px] leading-snug text-muted dark:text-muted-dark">
                    {donanaMeta.geographic_scope_es ||
                      (es
                        ? "Ámbito del Plan Especial al norte de la corona forestal; no es el inventario ICRA completo. Fuente: REDIAM / Junta de Andalucía."
                        : "Special Plan area north of the forest crown; not the full ICRA inventory. Source: REDIAM / Junta de Andalucía.")}
                  </p>
                </div>
              ) : null}

              {chg?.available !== false ? (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-ink dark:text-ink-dark">
                    {es ? "Capas CHG (abiertas)" : "CHG open layers"}
                  </p>
                  <div className="flex flex-wrap gap-4 text-xs text-muted dark:text-muted-dark">
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showSistemas}
                        onChange={(e) => setShowSistemas(e.target.checked)}
                      />
                      {es ? "Sistemas de explotación" : "Exploitation systems"}
                    </label>
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showDotacionOlivar}
                        onChange={(e) => setShowDotacionOlivar(e.target.checked)}
                      />
                      {es ? "Dotación olivar" : "Olive allotment"}
                    </label>
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showSobreexplotadas}
                        onChange={(e) => setShowSobreexplotadas(e.target.checked)}
                      />
                      {es ? "Zonas sobreexplotadas" : "Overexploited zones"}
                    </label>
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showVulnerables}
                        onChange={(e) => setShowVulnerables(e.target.checked)}
                      />
                      {es ? "Zonas vulnerables" : "Vulnerable zones"}
                    </label>
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showRecintos}
                        onChange={(e) => setShowRecintos(e.target.checked)}
                      />
                      {es ? "Recintos de riego (WMS)" : "Irrigation parcels (WMS)"}
                    </label>
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showBalsas}
                        onChange={(e) => setShowBalsas(e.target.checked)}
                      />
                      {es ? "Balsas" : "Ponds"}
                    </label>
                    <label className="inline-flex items-center gap-1.5 font-medium text-ink dark:text-ink-dark">
                      <input
                        type="checkbox"
                        checked={showPesEscasez}
                        onChange={(e) => setShowPesEscasez(e.target.checked)}
                      />
                      {es ? "Escasez PES" : "PES scarcity"}
                    </label>
                    <label className="inline-flex items-center gap-1.5 font-medium text-ink dark:text-ink-dark">
                      <input
                        type="checkbox"
                        checked={showPesSequia}
                        onChange={(e) => setShowPesSequia(e.target.checked)}
                      />
                      {es ? "Estado sequía PES" : "PES drought status"}
                    </label>
                    <label className="inline-flex items-center gap-1.5 font-medium text-ink dark:text-ink-dark">
                      <input
                        type="checkbox"
                        checked={showPiezometros}
                        onChange={(e) => setShowPiezometros(e.target.checked)}
                      />
                      {es ? "Piezómetros" : "Piezometers"}
                    </label>
                  </div>
                  {showPiezometros ? (
                    <label className="block text-[11px] text-muted dark:text-muted-dark">
                      {es ? "Filtrar piezómetros por provincia" : "Filter piezometers by province"}
                      <select
                        className="ml-2 rounded-md border border-black/10 bg-white px-2 py-0.5 text-xs dark:border-white/10 dark:bg-white/5"
                        value={filterPiezoProv}
                        onChange={(e) => setFilterPiezoProv(e.target.value)}
                      >
                        <option value="">{es ? "Todas" : "All"}</option>
                        <option value="Huelva">Huelva</option>
                        <option value="Sevilla">Sevilla</option>
                        <option value="Córdoba">Córdoba</option>
                        <option value="Jaén">Jaén</option>
                        <option value="Granada">Granada</option>
                        <option value="Málaga">Málaga</option>
                        <option value="Cádiz">Cádiz</option>
                        <option value="Almería">Almería</option>
                      </select>
                      <span className="ml-2 opacity-80">
                        {es
                          ? "(prioridad Doñana / Huelva–Sevilla)"
                          : "(Doñana / Huelva–Seville priority)"}
                      </span>
                    </label>
                  ) : null}
                  <p className="text-[11px] leading-snug text-muted dark:text-muted-dark">
                    {es
                      ? "PES = Plan Especial de Sequías CHG (no es ICRA). Piezómetros: series en visor IDE-CHG."
                      : "PES = CHG Special Drought Plan (not ICRA). Piezometers: series on IDE-CHG viewer."}
                    {piezoMeta?.series_url ? (
                      <>
                        {" "}
                        <a
                          className="text-terracotta underline-offset-2 hover:underline dark:text-terracotta-dark"
                          href={piezoMeta.series_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          IDE-CHG
                        </a>
                        .
                      </>
                    ) : null}{" "}
                    {chg?.note_es ||
                      (es
                        ? "Fuente: IDE-CHG / datos.gob.es. Geometrías simplificadas (~500 m)."
                        : "Source: IDE-CHG / datos.gob.es. Simplified geometries (~500 m).")}
                    {chgFetchedAt ? (
                      <span className="ml-1 opacity-80">
                        · {es ? "caché" : "cache"} {chgFetchedAt}
                      </span>
                    ) : null}
                  </p>
                  {chgStatus ? (
                    <p className="text-[11px] text-muted dark:text-muted-dark">{chgStatus}</p>
                  ) : null}
                </div>
              ) : null}

              {icraMeta ? (
                <div className="space-y-1 border-t border-black/5 pt-2 dark:border-white/5">
                  <p className="text-xs font-medium text-ink dark:text-ink-dark">
                    {es ? "ICRA (archivo, no mapa en vivo)" : "ICRA (archive, not a live map)"}
                  </p>
                  <p className="text-[11px] leading-snug text-muted dark:text-muted-dark">
                    {icraMeta.note_es ||
                      (es
                        ? "Inventario histórico 2002/2008: solo descarga en portalrediam; no son cuotas operativas."
                        : "Historical 2002/2008 inventory: download-only from portalrediam; not operational quotas.")}
                  </p>
                  <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                    {(icraMeta.links ?? []).map((lnk) => (
                      <li key={lnk.url}>
                        <a
                          className="text-terracotta underline-offset-2 hover:underline dark:text-terracotta-dark"
                          href={lnk.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {lnk.label_es || lnk.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}

          <MapContainer
            center={[37.25, -4.6]}
            zoom={7}
            className="z-0 h-[28rem] w-full overflow-hidden rounded-lg"
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution={
                showDonana ||
                showRecintos ||
                showSistemas ||
                showBalsas ||
                showDotacionOlivar ||
                showSobreexplotadas ||
                showVulnerables ||
                showPesSequia ||
                showPesEscasez ||
                showPiezometros
                  ? `${ATTR}${showDonana ? ` | ${REDIAM_ATTR}` : ""}${
                      showRecintos ||
                      showSistemas ||
                      showBalsas ||
                      showDotacionOlivar ||
                      showSobreexplotadas ||
                      showVulnerables ||
                      showPesSequia ||
                      showPesEscasez ||
                      showPiezometros
                        ? ` | ${CHG_ATTR}`
                        : ""
                    }`
                  : ATTR
              }
              url={TILE}
              subdomains="abcd"
            />
            {showDonana ? (
              <WMSTileLayer
                url={donanaWms.url}
                params={{
                  layers: donanaWms.layers,
                  format: donanaWms.format || "image/png",
                  transparent: donanaWms.transparent !== false,
                  version: donanaWms.version || "1.1.1",
                }}
                opacity={0.6}
                attribution={REDIAM_ATTR}
                zIndex={350}
              />
            ) : null}
            {showRecintos ? (
              <WMSTileLayer
                url={chgWms.url}
                params={{
                  layers: chgWms.layers,
                  format: chgWms.format || "image/png",
                  transparent: chgWms.transparent !== false,
                  version: chgWms.version || "1.1.1",
                }}
                opacity={0.55}
                attribution={CHG_ATTR}
              />
            ) : null}
            {showSistemas && sistemasFc ? (
              <GeoJSON
                key={`sistemas-${sistemasFc.features?.length ?? 0}`}
                data={sistemasFc}
                style={(feat) => {
                  const name =
                    (feat?.properties as { nom_sisexp?: string } | null)?.nom_sisexp || "";
                  return {
                    color: systemColor(name),
                    weight: 1.5,
                    fillColor: systemColor(name),
                    fillOpacity: 0.18,
                  };
                }}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as {
                    nom_sisexp?: string;
                    cod_sisexp?: string;
                    area_sisex?: number;
                  };
                  const ha =
                    p.area_sisex != null && Number.isFinite(Number(p.area_sisex))
                      ? ` · ${(Number(p.area_sisex) / 1e4).toFixed(0)} ha`
                      : "";
                  layer.bindTooltip(
                    `${p.nom_sisexp || "Sistema"}${p.cod_sisexp ? ` (${p.cod_sisexp})` : ""}${ha}`,
                  );
                }}
              />
            ) : null}
            {showBalsas && balsasFc ? (
              <GeoJSON
                key={`balsas-${balsasFc.features?.length ?? 0}`}
                data={balsasFc}
                style={() => ({
                  color: "#0369a1",
                  weight: 1,
                  fillColor: "#38bdf8",
                  fillOpacity: 0.45,
                })}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as { nom_balsa?: string; cod_balsa?: string };
                  layer.bindTooltip(p.nom_balsa || p.cod_balsa || "Balsa");
                }}
              />
            ) : null}
            {showDotacionOlivar && dotacionFc ? (
              <GeoJSON
                key={`dotacion-${dotacionFc.features?.length ?? 0}`}
                data={dotacionFc}
                style={() => ({
                  color: "#854d0e",
                  weight: 1,
                  fillColor: "#ca8a04",
                  fillOpacity: 0.28,
                })}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as {
                    pre?: number;
                    etp?: number;
                    tradicional?: number;
                    intensivo?: number;
                    superintensivo?: number;
                  };
                  const bits = [
                    p.tradicional != null ? `trad. ${p.tradicional}` : null,
                    p.intensivo != null ? `int. ${p.intensivo}` : null,
                    p.superintensivo != null ? `superint. ${p.superintensivo}` : null,
                    p.pre != null ? `P ${p.pre}` : null,
                    p.etp != null ? `ETP ${p.etp}` : null,
                  ].filter(Boolean);
                  layer.bindTooltip(`Dotación olivar${bits.length ? `: ${bits.join(" · ")}` : ""}`);
                }}
              />
            ) : null}
            {showSobreexplotadas && sobreFc ? (
              <GeoJSON
                key={`sobre-${sobreFc.features?.length ?? 0}`}
                data={sobreFc}
                style={() => ({
                  color: "#9f1239",
                  weight: 2,
                  fillColor: "#e11d48",
                  fillOpacity: 0.22,
                })}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as {
                    nom_zsobr?: string;
                    tipo_zsobr?: string;
                  };
                  layer.bindTooltip(
                    `${p.nom_zsobr || "Zona sobreexplotada"}${p.tipo_zsobr ? ` (${p.tipo_zsobr})` : ""}`,
                  );
                }}
              />
            ) : null}
            {showVulnerables && vulnFc ? (
              <GeoJSON
                key={`vuln-${vulnFc.features?.length ?? 0}`}
                data={vulnFc}
                style={() => ({
                  color: "#6b21a8",
                  weight: 1.5,
                  fillColor: "#a855f7",
                  fillOpacity: 0.18,
                  dashArray: "4 3",
                })}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as { nom_zprot?: string; euzprotcod?: string };
                  layer.bindTooltip(p.nom_zprot || p.euzprotcod || "Zona vulnerable");
                }}
              />
            ) : null}
            {showPesSequia && pesSequiaFc ? (
              <GeoJSON
                key={`pes-seq-${pesSequiaFc.features?.length ?? 0}`}
                data={pesSequiaFc}
                style={(feat) => {
                  const estado =
                    (feat?.properties as { estado?: string } | null)?.estado || "";
                  const col = estadoSequiaColor(estado);
                  return {
                    color: col,
                    weight: 1.2,
                    fillColor: col,
                    fillOpacity: 0.28,
                  };
                }}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as {
                    nom_szona?: string;
                    estado?: string;
                    indice?: number;
                    fecha?: string;
                  };
                  layer.bindTooltip(
                    `${p.nom_szona || "Zona"}: ${p.estado || "—"}${
                      p.indice != null ? ` (índice ${p.indice})` : ""
                    }${p.fecha ? ` · ${String(p.fecha).replace(/Z$/, "")}` : ""}`,
                  );
                }}
              />
            ) : null}
            {showPesEscasez && pesEscasezFc ? (
              <GeoJSON
                key={`pes-esc-${pesEscasezFc.features?.length ?? 0}`}
                data={pesEscasezFc}
                style={(feat) => {
                  const esc =
                    (feat?.properties as { escenario?: string } | null)?.escenario || "";
                  const col = escenarioColor(esc);
                  return {
                    color: col,
                    weight: 1.5,
                    fillColor: col,
                    fillOpacity: 0.32,
                  };
                }}
                onEachFeature={(feat, layer) => {
                  const p = (feat.properties || {}) as {
                    nom_ute?: string;
                    escenario?: string;
                    indicador?: number;
                    fecha?: string;
                  };
                  layer.bindTooltip(
                    `${p.nom_ute || "UTE"}: ${p.escenario || "—"}${
                      p.indicador != null ? ` (ind. ${p.indicador})` : ""
                    }${p.fecha ? ` · ${String(p.fecha).replace(/Z$/, "")}` : ""}`,
                  );
                }}
              />
            ) : null}
            {showPiezometros && piezoFiltered
              ? (piezoFiltered.features ?? []).map((feat, idx) => {
                  const g = feat.geometry as {
                    type?: string;
                    coordinates?: number[];
                  } | null;
                  if (!g || g.type !== "Point" || !g.coordinates || g.coordinates.length < 2) {
                    return null;
                  }
                  const [lon, lat] = g.coordinates;
                  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
                  const pr = (feat.properties || {}) as {
                    nom_estsub?: string;
                    massub?: string;
                    nom_muni?: string;
                    nom_prov?: string;
                    cota_estsub?: number;
                    profundidad?: string | number;
                    estado?: string;
                    cod_estsub?: string;
                  };
                  const key = pr.cod_estsub || `piezo-${idx}`;
                  return (
                    <CircleMarker
                      key={key}
                      center={[lat, lon]}
                      radius={3.5}
                      pathOptions={{
                        color: "#0f766e",
                        weight: 1,
                        fillColor: "#14b8a6",
                        fillOpacity: 0.85,
                      }}
                    >
                      <Tooltip direction="top" offset={[0, -2]}>
                        {pr.nom_estsub || pr.cod_estsub || "Piezómetro"}
                      </Tooltip>
                      <Popup>
                        <div className="max-w-xs text-sm">
                          <strong>{pr.nom_estsub || pr.cod_estsub || "Piezómetro"}</strong>
                          <div>
                            {pr.nom_muni || "—"}
                            {pr.nom_prov ? ` (${pr.nom_prov})` : ""}
                          </div>
                          {pr.massub ? <div className="text-xs opacity-80">{pr.massub}</div> : null}
                          <div className="text-xs opacity-80">
                            {pr.cota_estsub != null ? `Cota ${pr.cota_estsub} m` : ""}
                            {pr.profundidad != null && pr.profundidad !== ""
                              ? ` · prof. ${pr.profundidad} m`
                              : ""}
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })
              : null}
            {reservoirPts.map((r) => (
              <CircleMarker
                key={`r-${r.reservoir_code}`}
                center={[Number(r.lat), Number(r.lon)]}
                radius={7}
                pathOptions={{
                  color: "#1e293b",
                  weight: 1,
                  fillColor: systemColor(r.exploitation_system),
                  fillOpacity: 0.85,
                }}
              >
                <Tooltip direction="top" offset={[0, -4]}>
                  {r.reservoir_name}
                </Tooltip>
                <Popup>
                  <div className="max-w-xs text-sm">
                    <strong>{r.reservoir_name}</strong>
                    <div>{r.province_name}</div>
                    <div>
                      {es ? "Sistema" : "System"}: {r.exploitation_system}
                    </div>
                    <div>
                      {es ? "Estaciones enlazadas" : "Linked stations"}:{" "}
                      {r.linked_station_count ?? 0}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
            {stationPts.map((s) => (
              <CircleMarker
                key={`s-${s.station_code}`}
                center={[Number(s.lat), Number(s.lon)]}
                radius={5}
                pathOptions={{
                  color: systemColor(s.exploitation_system),
                  weight: 2,
                  fillColor: "#fff",
                  fillOpacity: 0.95,
                }}
              >
                <Tooltip direction="top" offset={[0, -2]}>
                  {s.station_name || s.station_code}
                </Tooltip>
                <Popup>
                  <div className="max-w-xs text-sm">
                    <strong>
                      {s.station_name || s.station_code} ({s.station_code})
                    </strong>
                    <div>{s.province_name}</div>
                    <div>
                      →{" "}
                      {s.reservoir_name
                        ? `${s.reservoir_name} (${s.exploitation_system})`
                        : s.exploitation_system || "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      {linkLabel(s.link_method, es)}
                      {s.distance_km != null ? ` · ${fmtKm(s.distance_km)}` : ""}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>

          {/* Legend by system (top systems present) */}
          <ul className="flex flex-wrap gap-3 text-xs text-muted dark:text-muted-dark">
            {(snap.by_system ?? []).slice(0, 12).map((sys) => (
              <li key={sys.exploitation_system} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm"
                  style={{ background: systemColor(sys.exploitation_system) }}
                />
                {sys.exploitation_system}
                <span className="tabular-nums opacity-70">({sys.station_count})</span>
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="text-xs font-medium text-terracotta underline-offset-2 hover:underline dark:text-terracotta-dark"
              onClick={() => setListOpen((v) => !v)}
            >
              {listOpen
                ? es
                  ? "Ocultar listado"
                  : "Hide list"
                : es
                  ? "Ver listado estación → embalse"
                  : "Show station → reservoir list"}
            </button>
            <button
              type="button"
              className="text-xs font-medium text-muted underline-offset-2 hover:underline dark:text-muted-dark"
              onClick={() => setShowCaveats((v) => !v)}
            >
              {showCaveats ? (es ? "Ocultar avisos" : "Hide caveats") : es ? "Avisos (estimación)" : "Caveats"}
            </button>
          </div>

          {showCaveats ? (
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted dark:text-muted-dark">
              {(snap.caveats_es ?? []).map((c) => (
                <li key={c}>{c}</li>
              ))}
              {(chg?.caveats_es ?? []).map((c) => (
                <li key={`chg-${c}`}>{c}</li>
              ))}
              {(openLayers?.caveats_es ?? []).map((c) => (
                <li key={`open-${c}`}>{c}</li>
              ))}
            </ul>
          ) : null}

          {listOpen ? (
            <div className="max-h-72 overflow-auto rounded-md border border-black/10 dark:border-white/10">
              <table className="w-full min-w-[40rem] text-left text-xs">
                <thead className="sticky top-0 bg-white dark:bg-ink-dark">
                  <tr className="border-b border-black/10 dark:border-white/10">
                    <th className="px-3 py-2 font-semibold">{es ? "Estación" : "Station"}</th>
                    <th className="px-3 py-2 font-semibold">{es ? "Provincia" : "Province"}</th>
                    <th className="px-3 py-2 font-semibold">{es ? "Embalse" : "Reservoir"}</th>
                    <th className="px-3 py-2 font-semibold">{es ? "Sistema" : "System"}</th>
                    <th className="px-3 py-2 font-semibold">{es ? "Dist." : "Dist."}</th>
                    <th className="px-3 py-2 font-semibold">{es ? "Regla" : "Rule"}</th>
                  </tr>
                </thead>
                <tbody>
                  {stations.slice(0, 200).map((s) => (
                    <tr
                      key={s.station_code}
                      className="border-b border-black/5 dark:border-white/5"
                    >
                      <td className="px-3 py-1.5">
                        <span
                          className="mr-1.5 inline-block h-2 w-2 rounded-full"
                          style={{ background: systemColor(s.exploitation_system) }}
                        />
                        {s.station_name || s.station_code}
                        <span className="ml-1 opacity-60">({s.station_code})</span>
                      </td>
                      <td className="px-3 py-1.5">{s.province_name || "—"}</td>
                      <td className="px-3 py-1.5">{s.reservoir_name || "—"}</td>
                      <td className="px-3 py-1.5">{s.exploitation_system || "—"}</td>
                      <td className="px-3 py-1.5 tabular-nums">{fmtKm(s.distance_km)}</td>
                      <td className={cn("px-3 py-1.5", "text-muted dark:text-muted-dark")}>
                        {linkLabel(s.link_method, es)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}

