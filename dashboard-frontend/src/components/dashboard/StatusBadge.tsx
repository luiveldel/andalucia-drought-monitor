import { useLocale } from "@/i18n/useT";
import { severityLabelFor } from "@/lib/severity";
import { cn } from "@/lib/utils";
import type { SeverityLevel } from "@/types/dashboard-model";

const tone: Record<SeverityLevel, string> = {
  normal: "bg-sev-normal/15 text-sev-normal border-sev-normal/40",
  warning: "bg-sev-alert/15 text-sev-alert border-sev-alert/40",
  emergency: "bg-sev-emergency/15 text-sev-emergency border-sev-emergency/40",
  critical: "bg-sev-critical/15 text-sev-critical border-sev-critical/40",
};

export function StatusBadge(props: { level: SeverityLevel; className?: string }) {
  const locale = useLocale();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        tone[props.level],
        props.className,
      )}
    >
      {severityLabelFor(locale, props.level)}
    </span>
  );
}
