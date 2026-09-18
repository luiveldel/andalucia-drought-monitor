import type { SeverityLevel } from "@/types/dashboard-model";

export const severityLabel: Record<SeverityLevel, string> = {
  normal: "Normal",
  warning: "Alerta",
  emergency: "Emergencia",
  critical: "Crítico",
};

export function severityRingClass(level: SeverityLevel): string {
  switch (level) {
    case "normal":
      return "border-sev-normal text-sev-normal";
    case "warning":
      return "border-sev-alert text-sev-alert";
    case "emergency":
      return "border-sev-emergency text-sev-emergency";
    case "critical":
      return "border-sev-critical text-sev-critical";
    default: {
      const _x: never = level;
      return _x;
    }
  }
}

export function severityFillClass(level: SeverityLevel): string {
  switch (level) {
    case "normal":
      return "bg-sev-normal/15";
    case "warning":
      return "bg-sev-alert/15";
    case "emergency":
      return "bg-sev-emergency/15";
    case "critical":
      return "bg-sev-critical/15";
    default: {
      const _x: never = level;
      return _x;
    }
  }
}

export function severityHex(level: SeverityLevel): string {
  switch (level) {
    case "normal":
      return "#3D7A3A";
    case "warning":
      return "#C98C00";
    case "emergency":
      return "#D96520";
    case "critical":
      return "#B83228";
    default: {
      const _x: never = level;
      return _x;
    }
  }
}
