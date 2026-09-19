import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useT } from "@/i18n/useT";
import { formatPct } from "@/lib/format";
import type { ReservoirRecord } from "@/types/dashboard-model";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState } from "react";

type SortKey = "reservoir" | "basin" | "fillPercentage" | "weeklyChange";

export function ReservoirTable(props: { rows: ReservoirRecord[] }) {
  const t = useT();
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "fillPercentage",
    dir: "asc",
  });

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    let list = props.rows.filter(
      (r) =>
        !s ||
        r.reservoir.toLowerCase().includes(s) ||
        r.basin.toLowerCase().includes(s) ||
        r.province.toLowerCase().includes(s),
    );
    list = [...list].sort((a, b) => {
      const mul = sort.dir === "asc" ? 1 : -1;
      switch (sort.key) {
        case "reservoir":
          return mul * a.reservoir.localeCompare(b.reservoir);
        case "basin":
          return mul * a.basin.localeCompare(b.basin);
        case "fillPercentage":
          return mul * (a.fillPercentage - b.fillPercentage);
        case "weeklyChange":
          return mul * (a.weeklyChange - b.weeklyChange);
      }
    });
    return list;
  }, [props.rows, q, sort]);

  function toggle(k: SortKey) {
    setSort((prev) =>
      prev.key === k ? { key: k, dir: prev.dir === "asc" ? "desc" : "asc" } : { key: k, dir: "asc" },
    );
  }

  const Th = (p: { k: SortKey; children: string }) => (
    <th className="sticky top-0 bg-surface px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted dark:bg-surface-dark dark:text-muted-dark">
      <button type="button" className="inline-flex items-center gap-1 hover:text-ink dark:hover:text-ink-dark" onClick={() => toggle(p.k)}>
        {p.children}
        {sort.key === p.k ? sort.dir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" /> : null}
      </button>
    </th>
  );

  return (
    <section>
      <SectionHeader title={t("section.reservoirs")} description={t("section.reservoirs.desc")} />
      <Card className="mt-3">
        <CardContent className="p-3">
          <div className="mb-3 max-w-xs">
            <Input placeholder={t("table.search")} value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 dark:border-white/10">
                  <Th k="reservoir">{t("table.reservoir")}</Th>
                  <Th k="basin">{t("table.basin")}</Th>
                  <th className="sticky top-0 bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted dark:bg-surface-dark dark:text-muted-dark">
                    {t("table.province")}
                  </th>
                  <th className="sticky top-0 bg-surface px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-muted dark:bg-surface-dark dark:text-muted-dark">
                    {t("table.capacity")}
                  </th>
                  <th className="sticky top-0 bg-surface px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-muted dark:bg-surface-dark dark:text-muted-dark">
                    {t("table.current")}
                  </th>
                  <Th k="fillPercentage">{t("table.fill")}</Th>
                  <Th k="weeklyChange">{t("table.weekly")}</Th>
                  <th className="sticky top-0 bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted dark:bg-surface-dark dark:text-muted-dark">
                    {t("table.status")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-black/5 transition-colors hover:bg-black/[0.03] dark:border-white/5 dark:hover:bg-white/[0.04]"
                  >
                    <td className="px-3 py-2 font-medium text-ink dark:text-ink-dark">{r.reservoir}</td>
                    <td className="px-3 py-2 text-muted dark:text-muted-dark">{r.basin}</td>
                    <td className="px-3 py-2 text-muted dark:text-muted-dark">{r.province}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink dark:text-ink-dark">{r.capacityHm3.toFixed(0)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink dark:text-ink-dark">{r.currentHm3.toFixed(0)}</td>
                    <td className="px-3 py-2 tabular-nums text-ink dark:text-ink-dark">{formatPct(r.fillPercentage)}</td>
                    <td className="px-3 py-2 tabular-nums text-ink dark:text-ink-dark">
                      {r.weeklyChange > 0 ? "+" : ""}
                      {r.weeklyChange.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge level={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
