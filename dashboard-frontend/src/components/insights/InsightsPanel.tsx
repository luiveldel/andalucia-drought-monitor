import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Card, CardContent } from "@/components/ui/card";

export function InsightsPanel(props: { insights: string[] }) {
  return (
    <Card className="h-full">
      <CardContent className="pt-4">
        <SectionHeader title="Lectura rápida" description="Narrativa automática del snapshot actual." />
        <ul className="mt-3 list-disc space-y-2 pl-4 text-sm leading-relaxed text-ink/90 dark:text-ink-dark/90">
          {props.insights.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
