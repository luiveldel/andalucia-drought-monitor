import "leaflet/dist/leaflet.css";
import { severityHex } from "@/lib/severity";
import type { ProvinceStatus } from "@/types/dashboard-model";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";

const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY as string | undefined)?.trim() || "";
const TILE_BASE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE = CARTO_KEY ? `${TILE_BASE}?api_key=${encodeURIComponent(CARTO_KEY)}` : TILE_BASE;
const ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO';

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

export function ProvinceStatusMap(props: { provinces: ProvinceStatus[] }) {
  const [fc, setFc] = useState<FeatureCollection | null>(null);
  useEffect(() => {
    let alive = true;
    void fetch("/andalusia-provinces.geojson")
      .then((r) => r.json())
      .then((d) => {
        if (alive) setFc(d as FeatureCollection);
      });
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

  if (!fc) {
    return <div className="h-80 animate-pulse rounded-lg bg-black/10 dark:bg-white/10" aria-busy />;
  }

  return (
    <MapContainer
      center={[37.25, -4.6]}
      zoom={7}
      className="z-0 h-80 w-full overflow-hidden rounded-lg"
      scrollWheelZoom={false}
    >
      <TileLayer attribution={ATTR} url={TILE} subdomains="abcd" />
      <FitBounds data={fc} />
      <GeoJSON
        data={fc}
        style={(feat) => {
          if (!feat || !feat.properties) {
            return { fillColor: "#94a3b8", fillOpacity: 0.2, color: "#333", weight: 1 };
          }
          const name = String((feat.properties as { name?: string }).name ?? "");
          const row = lookup.get(norm(name));
          const fill = row ? severityHex(row.severity) : "#94a3b8";
          return {
            fillColor: fill,
            fillOpacity: 0.42,
            color: "rgba(30,27,20,0.55)",
            weight: 1.2,
          };
        }}
      />
    </MapContainer>
  );
}
