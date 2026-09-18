import { GlobalFilters } from "@/components/dashboard/GlobalFilters";
import { Button } from "@/components/ui/button";
import { format, parseISO } from "date-fns";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function DashboardHeader(props: { updatedAt?: string }) {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  const label = props.updatedAt
    ? format(parseISO(props.updatedAt), "yyyy-MM-dd HH:mm")
    : "—";
  return (
    <header className="flex flex-col gap-4 border-b border-black/10 pb-6 dark:border-white/10 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-terracotta dark:text-terracotta-dark">
          Andalucía · resiliencia hídrica
        </p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight text-ink dark:text-ink-dark md:text-3xl">
          Monitor de sequía — panel de decisión
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted dark:text-muted-dark">
          Alertas, ranking de riesgo y contexto climático para priorizar actuaciones en embalses y provincias.
        </p>
        <p className="mt-2 text-xs font-medium tabular-nums text-muted dark:text-muted-dark">
          Última observación: <span className="text-ink dark:text-ink-dark">{label}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <GlobalFilters />
        <Button
          type="button"
          aria-label="Cambiar tema"
          onClick={() => setDark((d) => !d)}
          className="border-transparent p-2"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
