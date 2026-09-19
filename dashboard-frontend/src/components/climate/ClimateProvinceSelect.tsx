import { climateProvinceOptions, type ClimateProvince } from "@/constants/provinces";

export function ClimateProvinceSelect(props: {
  value: ClimateProvince;
  onChange: (value: ClimateProvince) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm sm:flex-row sm:items-center sm:gap-3">
      <span className="text-xs font-medium uppercase tracking-wide text-muted dark:text-muted-dark">
        Provincia
      </span>
      <select
        className="min-w-[12rem] rounded-md border border-black/15 bg-surface px-3 py-2 text-sm text-ink dark:border-white/15 dark:bg-surface-dark dark:text-ink-dark"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value as ClimateProvince)}
        aria-label="Seleccionar provincia para Clima"
      >
        {climateProvinceOptions().map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
    </label>
  );
}
