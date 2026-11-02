import { isStageComplete, STAGE_LABEL, STAGES, stageOf } from "../../lib/lifecycle";
import type { CaseDetail, Stage } from "../../lib/types";
import { cn } from "../../lib/utils";

export function LifecycleRail({ row }: { row: CaseDetail }) {
  const current = stageOf(row);

  return (
    <div className="flex flex-col gap-1.5">
      <ol
        className="flex items-center gap-1"
        aria-label={`Stage: ${STAGE_LABEL[current]}`}
      >
        {STAGES.map((stage: Stage, index) => {
          const done = isStageComplete(row, stage);
          const active = stage === current;
          const last = index === STAGES.length - 1;

          return (
            <li
              key={stage}
              className={cn("flex items-center gap-1", !last && "min-w-0 flex-1")}
            >
              {/* The stage in progress is bigger and ringed, not just a
                  different hue: cyan and emerald are hard to tell apart at six
                  pixels, so size carries the distinction and colour confirms
                  it. */}
              <span
                aria-hidden="true"
                className={cn(
                  "block shrink-0 rounded-full",
                  active && !done
                    ? "sz-stage-active h-2.5 w-2.5 bg-sz-water ring-2 ring-sz-water/30"
                    : "h-1.5 w-1.5",
                  done && "bg-sz-earth-fill",

                  !done && !active && "bg-sz-norm-fill/55",
                )}
              />
              {!last && (
                <span
                  aria-hidden="true"
                  className={cn(
                    "h-px min-w-0 flex-1",
                    done ? "bg-sz-earth-fill/50" : "bg-sz-norm-fill/35",
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>

      <p
        className={cn(
          "text-[11px]",
          current === "resolved" ? "text-sz-earth" : "text-sz-text-2",
        )}
      >
        {STAGE_LABEL[current]}
        {current === "triaging" && <span aria-hidden="true">…</span>}
      </p>
    </div>
  );
}
