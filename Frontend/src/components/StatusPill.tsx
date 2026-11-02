import type { ReactNode } from "react";

import { cn } from "../lib/utils";

export function StatusPill({
  children,
  tone,
  className,
  dot = false,
}: {
  children: ReactNode;

  tone: string;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] leading-tight font-medium whitespace-nowrap",
        tone,
        className,
      )}
    >
      {dot && <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
