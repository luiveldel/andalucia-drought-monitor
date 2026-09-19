/** Regional option for Clima province selector. */
export const CLIMATE_REGIONAL = "Andalucía";

export const ANDALUSIA_PROVINCES = [
  "Almería",
  "Cádiz",
  "Córdoba",
  "Granada",
  "Huelva",
  "Jaén",
  "Málaga",
  "Sevilla",
] as const;

export type AndalusiaProvince = (typeof ANDALUSIA_PROVINCES)[number];

export type ClimateProvince = typeof CLIMATE_REGIONAL | AndalusiaProvince;

export function climateProvinceOptions(): ClimateProvince[] {
  return [CLIMATE_REGIONAL, ...ANDALUSIA_PROVINCES];
}
