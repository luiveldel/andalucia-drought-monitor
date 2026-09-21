import { useT } from "@/i18n/useT";
import { cn } from "@/lib/utils";
import { useTabsStore, type DashboardTab } from "@/store/tabs.store";
import {
  ArrowLeftRight,
  ChevronLeft,
  ChevronRight,
  CloudRain,
  Droplets,
  Sprout,
  LayoutDashboard,
  Map,
  Scale,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

const TABS: { id: DashboardTab; key: "tab.overview" | "tab.decision" | "tab.map" | "tab.climate" | "tab.irrigation" | "tab.risk" | "tab.compare" | "tab.reservoirs"; icon: LucideIcon }[] = [
  { id: "overview", key: "tab.overview", icon: LayoutDashboard },
  { id: "decision", key: "tab.decision", icon: Scale },
  { id: "map", key: "tab.map", icon: Map },
  { id: "climate", key: "tab.climate", icon: CloudRain },
  { id: "irrigation", key: "tab.irrigation", icon: Sprout },
  { id: "risk", key: "tab.risk", icon: ShieldAlert },
  { id: "compare", key: "tab.compare", icon: ArrowLeftRight },
  { id: "reservoirs", key: "tab.reservoirs", icon: Droplets },
];

function NavButtons(props: { collapsed?: boolean; mobile?: boolean }) {
  const t = useT();
  const tab = useTabsStore((s) => s.tab);
  const setTab = useTabsStore((s) => s.setTab);
  const { collapsed, mobile } = props;

  return (
    <>
      {TABS.map((item) => {
        const Icon = item.icon;
        const active = tab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            title={collapsed && !mobile ? t(item.key) : undefined}
            onClick={() => setTab(item.id)}
            className={cn(
              "relative flex items-center gap-3 rounded-md text-sm font-medium transition-colors",
              mobile ? "h-9 shrink-0 px-3" : "h-9 w-full px-3",
              active
                ? "bg-terracotta/15 text-terracotta dark:bg-terracotta-dark/20 dark:text-terracotta-dark"
                : "text-muted hover:bg-black/5 hover:text-ink dark:text-muted-dark dark:hover:bg-white/5 dark:hover:text-ink-dark",
              collapsed && !mobile ? "justify-center" : "",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {(!collapsed || mobile) && <span className="truncate">{t(item.key)}</span>}
          </button>
        );
      })}
    </>
  );
}

/** Desktop left rail (Fares Desk–style). */
export function DashboardSidebar() {
  const t = useT();
  const collapsed = useTabsStore((s) => s.collapsed);
  const toggleCollapsed = useTabsStore((s) => s.toggleCollapsed);
  const setTab = useTabsStore((s) => s.setTab);

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-black/10 bg-surface/95 backdrop-blur-sm transition-all duration-200 dark:border-white/10 dark:bg-surface-dark/95 lg:flex",
        collapsed ? "w-14" : "w-52",
      )}
    >
      <div className="relative z-10 flex h-14 items-center border-b border-black/10 px-3 dark:border-white/10">
        <button
          type="button"
          onClick={() => setTab("overview")}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-terracotta/30",
            collapsed ? "justify-center" : "",
          )}
        >
          <img
            src="/brand/emblema-junta-andalucia-64.png"
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 shrink-0 object-contain"
            decoding="async"
          />
          {!collapsed && (
            <span className="min-w-0 overflow-hidden text-left">
              <span className="block truncate text-sm font-semibold text-ink dark:text-ink-dark">
                {t("nav.brand")}
              </span>
              <span className="block text-[10px] text-muted dark:text-muted-dark">
                {t("nav.tagline")}
              </span>
            </span>
          )}
        </button>
      </div>
      <nav
        className="relative z-10 flex-1 space-y-1 overflow-y-auto px-2 py-4"
        aria-label={t("tab.aria")}
        role="tablist"
      >
        <NavButtons collapsed={collapsed} />
      </nav>
      <div className="relative z-10 border-t border-black/10 px-2 py-2 dark:border-white/10">
        {!collapsed ? (
          <p className="px-1 text-[9px] leading-snug text-muted dark:text-muted-dark">
            <a
              className="underline-offset-2 hover:underline"
              href="https://github.com/luiveldel"
              target="_blank"
              rel="noreferrer"
            >
              {t("nav.attribution")}
            </a>
          </p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() => toggleCollapsed()}
        title={collapsed ? t("tab.expand") : t("tab.collapse")}
        aria-label={collapsed ? t("tab.expand") : t("tab.collapse")}
        className="absolute -right-3 top-[4.25rem] z-20 inline-flex h-6 w-6 items-center justify-center rounded-full border border-black/10 bg-surface text-muted shadow-sm transition-colors hover:bg-black/5 hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-terracotta/40 dark:border-white/10 dark:bg-surface-dark dark:text-muted-dark dark:hover:bg-white/5 dark:hover:text-ink-dark"
      >
        {collapsed ? (
          <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </button>
    </aside>
  );
}

/** Mobile horizontal tabs (visible below lg). */
export function DashboardMobileTabs() {
  const t = useT();
  return (
    <nav
      className="mb-4 flex gap-1 overflow-x-auto border-b border-black/10 pb-2 dark:border-white/10 lg:hidden"
      aria-label={t("tab.aria")}
      role="tablist"
    >
      <NavButtons mobile />
    </nav>
  );
}

/** @deprecated Prefer DashboardSidebar + DashboardMobileTabs */
export function DashboardTabs() {
  return <DashboardMobileTabs />;
}
