import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n/useT";

export function InsightsPanel(props: { insights: string[] }) {
  const t = useT();
  return (
    <Card className="flex min-h-[16rem] flex-1 flex-col">
      <CardContent className="flex flex-1 flex-col pt-4">
        <SectionHeader title={t("section.insights")} description={t("section.insights.desc")} />
        <ul className="mt-3 max-h-[22rem] flex-1 list-disc space-y-2 overflow-y-auto pl-4 text-sm leading-relaxed text-ink/90 dark:text-ink-dark/90">
          {props.insights.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
