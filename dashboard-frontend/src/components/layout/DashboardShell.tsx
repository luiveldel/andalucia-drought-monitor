import type { ReactNode } from "react";

export function DashboardShell(props: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas text-ink dark:bg-canvas-dark dark:text-ink-dark">
      <div className="mx-auto max-w-[1400px] px-4 py-8 md:px-8">{props.children}</div>
    </div>
  );
}
