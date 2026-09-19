/** Shared palettes for area sparklines and evolution charts. */

export const WATER_STROKE = "#1A6FA3";
export const WATER_FILL_TOP = "rgba(26, 111, 163, 0.42)";
export const WATER_FILL_MID = "rgba(26, 111, 163, 0.14)";
export const WATER_FILL_BOTTOM = "rgba(26, 111, 163, 0.02)";

/** Red / drought tone — lack of water (deficit, stress). */
export const STRESS_STROKE = "#B84A1B";
export const STRESS_FILL_TOP = "rgba(184, 74, 27, 0.42)";
export const STRESS_FILL_MID = "rgba(184, 74, 27, 0.14)";
export const STRESS_FILL_BOTTOM = "rgba(184, 74, 27, 0.02)";

export type ChartTone = {
  stroke: string;
  fillTop: string;
  fillMid: string;
  fillBottom: string;
};

const WATER_TONE: ChartTone = {
  stroke: WATER_STROKE,
  fillTop: WATER_FILL_TOP,
  fillMid: WATER_FILL_MID,
  fillBottom: WATER_FILL_BOTTOM,
};

const STRESS_TONE: ChartTone = {
  stroke: STRESS_STROKE,
  fillTop: STRESS_FILL_TOP,
  fillMid: STRESS_FILL_MID,
  fillBottom: STRESS_FILL_BOTTOM,
};

const STRESS_IDS = new Set(["deficit", "stress"]);

/** Blue for water abundance metrics; terracotta/red for scarcity problems. */
export function chartToneForId(id: string): ChartTone {
  return STRESS_IDS.has(id) ? STRESS_TONE : WATER_TONE;
}
