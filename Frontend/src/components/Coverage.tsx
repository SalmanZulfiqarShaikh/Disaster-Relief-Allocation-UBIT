import { Clock, Languages, MapPin, UserCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Reveal } from "./Reveal";

const ITEMS: Array<{
  icon: LucideIcon;
  label: string;
  note: string;
}> = [
  { icon: MapPin, label: "areas across Karachi", note: "All seven districts" },
  { icon: Clock, label: "to the first reply", note: "Never waits for a human" },
  { icon: Languages, label: "ways to write it", note: "English, Urdu, Roman Urdu" },
  { icon: UserCheck, label: "manual step", note: "The official handoff" },
];

const SEEDED_AREAS = 78;

export function Coverage({ areaCount }: { areaCount: number | null }) {
  const values = [
    String(areaCount && areaCount > 0 ? areaCount : SEEDED_AREAS),
    "<5s",
    "Any",
    "One",
  ];

  return (
    <section
      aria-label="Coverage"
      className="border-y border-sz-line bg-sz-raised/60"
    >
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <ul className="grid grid-cols-2 divide-sz-line sm:divide-x lg:grid-cols-4">
          {ITEMS.map((item, index) => (
            <Reveal key={item.label} delay={index * 0.05}>
              <li className="flex h-full items-start gap-3 px-0 py-5 sm:px-5 lg:py-6">
                <item.icon
                  className="mt-1 h-4.5 w-4.5 shrink-0 text-sz-water"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="font-mono text-[1.4rem] leading-none tabular-nums">
                    {values[index]}
                  </p>
                  <p className="mt-1.5 text-[13.5px] leading-snug text-sz-text-2">
                    {item.label}
                  </p>
                  <p className="mt-0.5 text-[12px] text-sz-text-3">{item.note}</p>
                </div>
              </li>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
