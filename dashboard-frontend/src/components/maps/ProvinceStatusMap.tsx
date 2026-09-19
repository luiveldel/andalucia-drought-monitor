import "leaflet/dist/leaflet.css";
import { severityHex } from "@/lib/severity";
import type { ProvinceStatus } from "@/types/dashboard-model";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";

const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY as string | undefined)?.trim() || "";
const TILE_BASE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
// Carto Basemaps require query param `key` (not api_key).
const TILE = CARTO_KEY ? `${TILE_BASE}?key=${encodeURIComponent(CARTO_KEY)}` : TILE_BASE;
const ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO';

function norm(s: string) {
  return s
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .trim();
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

export function ProvinceStatusMap(props: { provinces: ProvinceStatus[] }) {
  const [provincesFc, setProvincesFc] = useState<FeatureCollection | null>(null);
  const [zonesFc, setZonesFc] = useState<FeatureCollection | null>(null);
  const [showZones, setShowZones] = useState(true);
  const [sourceLabel, setSourceLabel] = useState("…");

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
    return <div className="h-80 animate-pulse rounded-lg bg-black/10 dark:bg-white/10" aria-busy />;
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted dark:text-muted-dark">
        <span>Límites: {sourceLabel}</span>
        <label className="inline-flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={showZones}
            onChange={(e) => setShowZones(e.target.checked)}
          />
          Capas GIS zonas / provincias (Andalucía)
        </label>
      </div>
      <MapContainer
        center={[37.25, -4.6]}
        zoom={7}
        className="z-0 h-96 w-full overflow-hidden rounded-lg"
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
            const fill = row ? severityHex(row.severity) : "#94a3b8";
            return {
              fillColor: fill,
              fillOpacity: 0.45,
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
            const tip = row
              ? `${row.province}: ${row.fillPercentage.toFixed(1)}% · ${row.severity}`
              : name;
            layer.bindTooltip(tip, { sticky: true });
          }}
        />
      </MapContainer>
    </div>
  );
}
