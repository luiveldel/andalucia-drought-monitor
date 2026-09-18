import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center rounded-md border border-black/15 bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-black/5 dark:border-white/15 dark:bg-surface-dark dark:text-ink-dark dark:hover:bg-white/10",
        className,
      )}
      {...props}
    />
  );
}
