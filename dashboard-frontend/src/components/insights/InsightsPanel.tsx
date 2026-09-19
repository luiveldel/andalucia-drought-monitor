import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n/useT";

export function InsightsPanel(props: { insights: string[] }) {
  const t = useT();
  // Keep the sidebar compact so it does not collide with sections below.
  const items = props.insights.slice(0, 4);
  return (
    <Card className="max-h-56 shrink-0">
      <CardContent className="pt-4">
        <SectionHeader title={t("section.insights")} description={t("section.insights.desc")} />
        <ul className="mt-2 max-h-32 list-disc space-y-1.5 overflow-y-auto pl-4 text-sm leading-snug text-ink/90 dark:text-ink-dark/90">
          {items.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
