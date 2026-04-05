import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type BadgeProps = {
  className?: string;
  children: ReactNode;
};

export function Badge({ className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-electric-400/20 bg-electric-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-electric-400",
        className,
      )}
    >
      {children}
    </span>
  );
}
