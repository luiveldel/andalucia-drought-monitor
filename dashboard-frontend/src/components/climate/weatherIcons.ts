const ICONS: Record<string, string> = {
  sunny: "☀️",
  partly_cloudy: "⛅",
  cloudy: "☁️",
  rain: "🌧️",
  drizzle: "🌦️",
  storm: "⛈️",
  snow: "🌨️",
  fog: "🌫️",
  heat: "🔥",
  storm_risk: "⚡",
};

export function weatherEmoji(condition?: string | null): string {
  if (!condition) return "🌡️";
  return ICONS[condition] ?? "🌡️";
}
