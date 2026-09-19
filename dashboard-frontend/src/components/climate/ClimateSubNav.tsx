import { cn } from "@/lib/utils";

export type ClimateSubTab = "forecast" | "observed";

const ITEMS: { id: ClimateSubTab; label: string; description: string }[] = [
  {
    id: "forecast",
    label: "Pronóstico",
    description: "AEMET / Open-Meteo · horizonte corto",
  },
  {
    id: "observed",
    label: "Observado y riesgo",
    description: "RIA, SPI, anomalías y estrés",
  },
];

export function ClimateSubNav(props: {
  value: ClimateSubTab;
  onChange: (tab: ClimateSubTab) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Subsecciones de Clima"
      className="flex flex-wrap gap-2 rounded-xl border border-black/10 bg-black/[0.02] p-1 dark:border-white/10 dark:bg-white/[0.03]"
    >
      {ITEMS.map((item) => {
        const active = props.value === item.id;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => props.onChange(item.id)}
            className={cn(
              "min-w-[10rem] flex-1 rounded-lg px-3 py-2 text-left transition-colors",
              active
                ? "bg-white shadow-sm dark:bg-white/10"
                : "hover:bg-white/60 dark:hover:bg-white/5",
            )}
          >
            <span
              className={cn(
                "block text-sm font-semibold",
                active ? "text-terracotta dark:text-terracotta-dark" : "text-ink dark:text-ink-dark",
              )}
            >
              {item.label}
            </span>
            <span className="mt-0.5 block text-[11px] text-muted dark:text-muted-dark">
              {item.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
