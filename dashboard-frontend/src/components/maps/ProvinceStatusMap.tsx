import "leaflet/dist/leaflet.css";
import { severityHex } from "@/lib/severity";
import type { IrrigationRiskLevel, ProvinceStatus } from "@/types/dashboard-model";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";

const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY as string | undefined)?.trim() || "";
const TILE_BASE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE = CARTO_KEY ? `${TILE_BASE}?key=${encodeURIComponent(CARTO_KEY)}` : TILE_BASE;
const ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO';

export type MapColorMode = "fill" | "irrigation";

function norm(s: string) {
  return s
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .trim();
}

function irrigationHex(level: IrrigationRiskLevel | undefined): string {
  switch (level) {
    case "critical":
      return "#B83228";
    case "warning":
      return "#C98C00";
    case "watch":
      return "#0284c7";
    case "ok":
      return "#3D7A3A";
    default:
      return "#94a3b8";
  }
}

function irrigationLabel(level: IrrigationRiskLevel | undefined): string {
  switch (level) {
    case "critical":
      return "Crítico";
    case "warning":
      return "Alerta";
    case "watch":
      return "Vigilancia";
    case "ok":
      return "Holgado";
    default:
      return "Sin dato";
  }
}

function FitBounds({ data }: { data: FeatureCollection }) {
  const map = useMap();
  useEffect(() => {
    const layer = L.geoJSON(data as never);
    const b = layer.getBounds();
    if (b.isValid()) {
      map.fitBounds(b, { padding: [20, 20], maxZoom: 9 });
    }
  }, [map, data]);
  return null;
}

async function fetchFc(urls: string[]): Promise<FeatureCollection | null> {
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (!r.ok) continue;
      const d = (await r.json()) as FeatureCollection;
      if (d?.features?.length) return d;
    } catch {
      /* try next */
    }
  }
  return null;
}

function Legend(props: { mode: MapColorMode }) {
  if (props.mode === "irrigation") {
    const items: Array<{ level: IrrigationRiskLevel; label: string }> = [
      { level: "critical", label: "Crítico" },
      { level: "warning", label: "Alerta" },
      { level: "watch", label: "Vigilancia" },
      { level: "ok", label: "Holgado" },
    ];
    return (
      <ul className="flex flex-wrap gap-3 text-xs text-muted dark:text-muted-dark">
        {items.map((it) => (
          <li key={it.level} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: irrigationHex(it.level) }}
            />
            {it.label}
          </li>
        ))}
      </ul>
    );
  }
  const items = [
    { level: "critical" as const, label: "Crítico" },
    { level: "emergency" as const, label: "Emergencia" },
    { level: "warning" as const, label: "Alerta" },
    { level: "normal" as const, label: "Normal" },
  ];
  return (
    <ul className="flex flex-wrap gap-3 text-xs text-muted dark:text-muted-dark">
      {items.map((it) => (
        <li key={it.level} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: severityHex(it.level) }}
          />
          {it.label}
        </li>
      ))}
    </ul>
  );
}

export function ProvinceStatusMap(props: {
  provinces: ProvinceStatus[];
  /** Default color mode. */
  defaultMode?: MapColorMode;
  /** Hide mode toggle (fixed mode). */
  modeFixed?: boolean;
  className?: string;
  heightClass?: string;
}) {
  const [provincesFc, setProvincesFc] = useState<FeatureCollection | null>(null);
  const [zonesFc, setZonesFc] = useState<FeatureCollection | null>(null);
  const [showZones, setShowZones] = useState(false);
  const [sourceLabel, setSourceLabel] = useState("…");
  const [mode, setMode] = useState<MapColorMode>(props.defaultMode ?? "irrigation");

  useEffect(() => {
    let alive = true;
    void (async () => {
      const fromApi = await fetchFc(["/api/gis/provinces.geojson"]);
      const fallback = fromApi ? null : await fetchFc(["/andalusia-provinces.geojson"]);
      const fc = fromApi ?? fallback;
      if (!alive) return;
      setProvincesFc(fc);
      setSourceLabel(fromApi ? "PostGIS (dim_provinces_polygons)" : "GeoJSON estático");
      const zones = await fetchFc(["/api/gis/agricultural-zones.geojson"]);
      if (alive) setZonesFc(zones);
    })();
    return () => {
      alive = false;
    };
  }, []);

  const lookup = useMemo(() => {
    const m = new Map<string, ProvinceStatus>();
    for (const p of props.provinces) {
      m.set(norm(p.province), p);
    }
    return m;
  }, [props.provinces]);

  if (!provincesFc) {
    return (
      <div
        className={`${props.heightClass ?? "h-80"} animate-pulse rounded-lg bg-black/10 dark:bg-white/10`}
        aria-busy
      />
    );
  }

  return (
    <div className={`space-y-2 ${props.className ?? ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted dark:text-muted-dark">
        <span>Límites: {sourceLabel}</span>
        <div className="flex flex-wrap items-center gap-3">
          {!props.modeFixed ? (
            <div className="inline-flex rounded-lg border border-black/10 p-0.5 dark:border-white/10">
              <button
                type="button"
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                  mode === "irrigation"
                    ? "bg-terracotta/15 text-terracotta dark:bg-terracotta-dark/20 dark:text-terracotta-dark"
                    : "text-muted dark:text-muted-dark"
                }`}
                onClick={() => setMode("irrigation")}
              >
                Autonomía riego
              </button>
              <button
                type="button"
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                  mode === "fill"
                    ? "bg-terracotta/15 text-terracotta dark:bg-terracotta-dark/20 dark:text-terracotta-dark"
                    : "text-muted dark:text-muted-dark"
                }`}
                onClick={() => setMode("fill")}
              >
                Llenado embalse
              </button>
            </div>
          ) : null}
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={showZones}
              onChange={(e) => setShowZones(e.target.checked)}
            />
            Zonas agrarias
          </label>
        </div>
      </div>
      <Legend mode={mode} />
      <MapContainer
        center={[37.25, -4.6]}
        zoom={7}
        className={`z-0 w-full overflow-hidden rounded-lg ${props.heightClass ?? "h-96"}`}
        scrollWheelZoom={false}
      >
        <TileLayer attribution={ATTR} url={TILE} subdomains="abcd" />
        <FitBounds data={provincesFc} />
        {showZones && zonesFc ? (
          <GeoJSON
            data={zonesFc}
            style={() => ({
              fillColor: "#c4a574",
              fillOpacity: 0.12,
              color: "#8b6914",
              weight: 1,
              dashArray: "4 3",
            })}
          />
        ) : null}
        <GeoJSON
          key={mode}
          data={provincesFc}
          style={(feat) => {
            if (!feat || !feat.properties) {
              return { fillColor: "#94a3b8", fillOpacity: 0.2, color: "#333", weight: 1 };
            }
            const name = String(
              (feat.properties as { name?: string; province_name?: string }).name ??
                (feat.properties as { province_name?: string }).province_name ??
                "",
            );
            const row = lookup.get(norm(name));
            const fill =
              mode === "irrigation"
                ? irrigationHex(row?.irrigationRiskLevel)
                : row
                  ? severityHex(row.severity)
                  : "#94a3b8";
            return {
              fillColor: fill,
              fillOpacity: 0.5,
              color: "rgba(30,27,20,0.65)",
              weight: 1.4,
            };
          }}
          onEachFeature={(feat, layer) => {
            const name = String(
              (feat.properties as { name?: string })?.name ??
                (feat.properties as { province_name?: string })?.province_name ??
                "",
            );
            const row = lookup.get(norm(name));
            let tip = name;
            if (row) {
              if (mode === "irrigation") {
                const days =
                  row.irrigationDaysAutonomy != null
                    ? `${row.irrigationDaysAutonomy.toFixed(0)} d autonomía`
                    : "sin autonomía";
                const until =
                  row.daysUntilCritical === 0
                    ? "ya crítico"
                    : row.daysUntilCritical != null
                      ? `${row.daysUntilCritical} d hasta crítico`
                      : null;
                tip = `${row.province}: ${irrigationLabel(row.irrigationRiskLevel)} · ${days}${
                  until ? ` · ${until}` : ""
                }`;
              } else {
                tip = `${row.province}: ${row.fillPercentage.toFixed(1)}% · ${row.severity}`;
              }
            }
            layer.bindTooltip(tip, { sticky: true });
          }}
        />
      </MapContainer>
    </div>
  );
}
