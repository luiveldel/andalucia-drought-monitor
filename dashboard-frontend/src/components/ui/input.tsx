import { cn } from "@/lib/utils";
import type { InputHTMLAttributes } from "react";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-black/15 bg-surface px-3 py-2 text-sm text-ink outline-none ring-water focus:ring-1 dark:border-white/15 dark:bg-surface-dark dark:text-ink-dark",
        className,
      )}
      {...props}
    />
  );
}
