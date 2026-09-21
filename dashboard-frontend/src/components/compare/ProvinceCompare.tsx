import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { severityLabel } from "@/lib/severity";
import { cn } from "@/lib/utils";
import type { ProvinceCompareResponse, SeverityLevel } from "@/types/dashboard-model";
import { useMemo, useState } from "react";

const ANDALUSIAN = [
  "Almería",
  "Cádiz",
  "Córdoba",
  "Granada",
  "Huelva",
  "Jaén",
  "Málaga",
  "Sevilla",
] as const;

function MetricRow(props: {
  label: string;
  left: string;
  right: string;
  better?: "left" | "right" | "none";
}) {
  return (
    <div className="grid grid-cols-3 gap-2 border-t border-black/5 py-2 text-sm dark:border-white/5">
      <div className="text-muted dark:text-muted-dark">{props.label}</div>
      <div
        className={cn(
          "tabular-nums font-medium",
          props.better === "left" && "text-sev-normal",
          props.better === "right" && "text-muted dark:text-muted-dark",
        )}
      >
        {props.left}
      </div>
      <div
        className={cn(
          "tabular-nums font-medium",
          props.better === "right" && "text-sev-normal",
          props.better === "left" && "text-muted dark:text-muted-dark",
        )}
      >
        {props.right}
      </div>
    </div>
  );
}

function fmt(n: number | undefined | null, digits = 1, suffix = "") {
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return `${n.toFixed(digits)}${suffix}`;
}

export function ProvinceCompare(props: { provinceNames?: string[] }) {
  const options = props.provinceNames?.length ? props.provinceNames : [...ANDALUSIAN];
  const [a, setA] = useState(options[0] ?? "Sevilla");
  const [b, setB] = useState(options[1] ?? "Córdoba");
  const [data, setData] = useState<ProvinceCompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = a && b && a !== b;

  async function runCompare() {
    if (!canRun) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
      if (!res.ok) throw new Error(await res.text());
      setData((await res.json()) as ProvinceCompareResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al comparar");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const rows = useMemo(() => {
    if (!data) return [];
    const L = data.a;
    const R = data.b;
    const labels = data.labels_es;
    const sev = (s?: SeverityLevel) => (s ? severityLabel[s] : "—");
    const betterFill = (L.fill_pct ?? 0) >= (R.fill_pct ?? 0) ? "left" : "right";
    const betterRisk = (L.risk_score ?? 100) <= (R.risk_score ?? 100) ? "left" : "right";
    const betterSpi = (() => {
      const la = L.spi?.spi_value;
      const rb = R.spi?.spi_value;
      if (la == null || rb == null) return "none" as const;
      return la >= rb ? ("left" as const) : ("right" as const);
    })();
    return [
      {
        label: labels.fill_pct ?? "Llenado",
        left: fmt(L.fill_pct, 1, "%"),
        right: fmt(R.fill_pct, 1, "%"),
        better: betterFill as "left" | "right",
      },
      {
        label: labels.severity ?? "Severidad",
        left: sev(L.severity),
        right: sev(R.severity),
        better: "none" as const,
      },
      {
        label: labels.risk_score ?? "Riesgo",
        left: fmt(L.risk_score, 1),
        right: fmt(R.risk_score, 1),
        better: betterRisk as "left" | "right",
      },
      {
        label: labels.trend_7d ?? "Δ 7d",
        left: fmt(L.trend_7d, 1, " pp"),
        right: fmt(R.trend_7d, 1, " pp"),
        better: "none" as const,
      },
      {
        label: labels.stress ?? "Estrés",
        left: fmt(L.stress, 3),
        right: fmt(R.stress, 3),
        better: "none" as const,
      },
      {
        label: labels.deficit_mm ?? "Déficit",
        left: fmt(L.deficit_mm, 2, " mm"),
        right: fmt(R.deficit_mm, 2, " mm"),
        better: "none" as const,
      },
      {
        label: labels.spi ?? "SPI provisional",
        left: L.spi?.spi_value != null ? `${L.spi.spi_value.toFixed(2)} (${L.spi.spi_class_es ?? "—"})` : "—",
        right: R.spi?.spi_value != null ? `${R.spi.spi_value.toFixed(2)} (${R.spi.spi_class_es ?? "—"})` : "—",
        better: betterSpi,
      },
    ];
  }, [data]);

  return (
    <section className="space-y-3">
      <SectionHeader
        title="Comparativa provincia A vs B"
        description="Elige dos provincias andaluzas y contrasta llenado, severidad, riesgo, SPI y tendencias con datos vivos."
      />
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs uppercase text-muted dark:text-muted-dark">Provincia A</span>
              <select
                className="rounded-md border border-black/15 bg-surface px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
                value={a}
                onChange={(e) => setA(e.target.value)}
              >
                {options.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs uppercase text-muted dark:text-muted-dark">Provincia B</span>
              <select
                className="rounded-md border border-black/15 bg-surface px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
                value={b}
                onChange={(e) => setB(e.target.value)}
              >
                {options.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <Button type="button" disabled={!canRun || loading} onClick={() => void runCompare()}>
              {loading ? "Comparando…" : "Comparar"}
            </Button>
          </div>
          {error ? <p className="text-sm text-sev-critical">{error}</p> : null}
          {data ? (
            <div>
              <div className="grid grid-cols-3 gap-2 text-sm font-semibold">
                <div />
                <div>{data.a.province}</div>
                <div>{data.b.province}</div>
              </div>
              {rows.map((r) => (
                <MetricRow key={r.label} {...r} />
              ))}
              {(!data.a.found || !data.b.found) && (
                <p className="mt-2 text-xs text-muted dark:text-muted-dark">
                  Alguna provincia aún no tiene datos para la fecha más reciente.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted dark:text-muted-dark">
              Pulsa «Comparar» para cargar métricas desde la API (sin mocks).
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
