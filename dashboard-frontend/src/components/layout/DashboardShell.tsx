import { DashboardSidebar } from "@/components/dashboard/DashboardTabs";
import { useTabsStore } from "@/store/tabs.store";
import type { ReactNode } from "react";

export function DashboardShell(props: { children: ReactNode }) {
  const collapsed = useTabsStore((s) => s.collapsed);
  return (
    <div className="min-h-screen bg-canvas text-ink dark:bg-canvas-dark dark:text-ink-dark">
      <DashboardSidebar />
      <div
        className={`transition-all duration-200 ${
          collapsed ? "lg:pl-14" : "lg:pl-52"
        }`}
      >
        <div className="mx-auto max-w-[1400px] px-4 py-6 md:px-8 md:py-8">{props.children}</div>
      </div>
    </div>
  );
}
