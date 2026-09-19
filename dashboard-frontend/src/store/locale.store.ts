import { create } from "zustand";

export type Locale = "es" | "en";

function readInitial(): Locale {
  try {
    const v = localStorage.getItem("agro-dashboard-locale");
    if (v === "en" || v === "es") return v;
  } catch {
    /* ignore */
  }
  return "es";
}

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
}

export const useLocaleStore = create<LocaleState>((set, get) => ({
  locale: typeof window === "undefined" ? "es" : readInitial(),
  setLocale: (locale) => {
    try {
      localStorage.setItem("agro-dashboard-locale", locale);
    } catch {
      /* ignore */
    }
    set({ locale });
  },
  toggleLocale: () => {
    const next = get().locale === "es" ? "en" : "es";
    try {
      localStorage.setItem("agro-dashboard-locale", next);
    } catch {
      /* ignore */
    }
    set({ locale: next });
  },
}));
