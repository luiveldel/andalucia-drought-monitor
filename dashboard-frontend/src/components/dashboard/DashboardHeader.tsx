import { GlobalFilters } from "@/components/dashboard/GlobalFilters";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n/useT";
import { useLocaleStore } from "@/store/locale.store";
import { format, parseISO } from "date-fns";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function DashboardHeader(props: { updatedAt?: string }) {
  const t = useT();
  const locale = useLocaleStore((s) => s.locale);
  const toggleLocale = useLocaleStore((s) => s.toggleLocale);
  const [dark, setDark] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  const label = props.updatedAt
    ? format(parseISO(props.updatedAt), "yyyy-MM-dd HH:mm")
    : "—";
  return (
    <header className="flex flex-col gap-4 border-b border-black/10 pb-6 dark:border-white/10 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-terracotta dark:text-terracotta-dark">
          {t("brand.kicker")}
        </p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight text-ink dark:text-ink-dark md:text-3xl">
          {t("brand.title")}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted dark:text-muted-dark">{t("brand.subtitle")}</p>
        <p className="mt-2 text-xs font-medium tabular-nums text-muted dark:text-muted-dark">
          {t("brand.updated")} <span className="text-ink dark:text-ink-dark">{label}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <GlobalFilters />
        <Button
          type="button"
          aria-label={t("lang.aria")}
          onClick={() => toggleLocale()}
          className="min-w-[3rem] px-3 font-semibold tracking-wide"
        >
          {locale === "es" ? t("lang.toEn") : t("lang.toEs")}
        </Button>
        <Button
          type="button"
          aria-label={t("theme.toggle")}
          onClick={() => setDark((d) => !d)}
          className="border-transparent p-2"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
