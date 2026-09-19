import { t, type MessageKey } from "@/i18n/messages";
import { useLocaleStore } from "@/store/locale.store";

export function useT() {
  const locale = useLocaleStore((s) => s.locale);
  return (key: MessageKey) => t(locale, key);
}

export function useLocale() {
  return useLocaleStore((s) => s.locale);
}
