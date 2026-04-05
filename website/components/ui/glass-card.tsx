import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type GlassCardProps = {
  className?: string;
  children: ReactNode;
};

export function GlassCard({ className, children }: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-[28px] border border-white/10 bg-white/[0.05] p-6 shadow-card backdrop-blur-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
