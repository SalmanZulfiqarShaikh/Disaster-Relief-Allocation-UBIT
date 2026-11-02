import { cn } from "../lib/utils";

export function SimulatedTag({
  children = "Simulated",
  className,
  title,
}: {
  children?: string;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-sz-line bg-sz-panel px-2 py-0.5 text-[11px] whitespace-nowrap text-sz-text-2",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="sz-hatch block h-2.5 w-2.5 shrink-0 border border-current text-sz-text-3"
      />
      {children}
    </span>
  );
}

export function SimulatedSwatch({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "sz-hatch block h-3 w-3 shrink-0 border border-current text-sz-norm",
        className,
      )}
    />
  );
}
