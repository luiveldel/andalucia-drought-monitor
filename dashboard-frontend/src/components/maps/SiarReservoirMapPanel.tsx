"use client";

import "leaflet/dist/leaflet.css";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import type {
  IrrigationAutonomySnapshot,
  StationReservoirLink,
  StationReservoirLinksSnapshot,
  StationReservoirMarker,
} from "@/types/dashboard-model";
import { useT } from "@/i18n/useT";
import { useLocaleStore } from "@/store/locale.store";
import { cn } from "@/lib/utils";
import { useMemo, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";

const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY as string | undefined)?.trim() || "";
const TILE_BASE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE = CARTO_KEY ? `${TILE_BASE}?key=${encodeURIComponent(CARTO_KEY)}` : TILE_BASE;
const ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO';

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
  const [filterSystem, setFilterSystem] = useState<string>("");
  const [showCaveats, setShowCaveats] = useState(false);
  const [listOpen, setListOpen] = useState(false);

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

          <MapContainer
            center={[37.25, -4.6]}
            zoom={7}
            className="z-0 h-[28rem] w-full overflow-hidden rounded-lg"
            scrollWheelZoom={false}
          >
            <TileLayer attribution={ATTR} url={TILE} subdomains="abcd" />
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

