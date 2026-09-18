export function formatPct(n: number, digits = 1): string {
  return `${n.toFixed(digits)}%`;
}

export function formatHm3(n: number, digits = 1): string {
  return `${n.toFixed(digits)} hm³`;
}

export function formatDelta(n: number, unit: string): string {
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}${unit}`;
}
