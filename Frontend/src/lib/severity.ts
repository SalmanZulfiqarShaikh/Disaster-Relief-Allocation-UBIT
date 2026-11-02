

import type { Category, DispatchStatus, OfferStatus, ProtocolNode } from "./types";

export type Severity = "critical" | "elevated" | "normal";

export function severityOf(score: number): Severity {
  if (score >= 0.7) return "critical";
  if (score >= 0.4) return "elevated";
  return "normal";
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  elevated: "Elevated",
  normal: "Normal",
};

export const SEVERITY_TEXT: Record<Severity, string> = {
  critical: "text-sz-crit",
  elevated: "text-sz-elev",
  normal: "text-sz-norm",
};

export const SEVERITY_BG: Record<Severity, string> = {
  critical: "bg-sz-crit-fill",
  elevated: "bg-sz-elev-fill",
  normal: "bg-sz-norm-fill",
};

export const SEVERITY_RING: Record<Severity, string> = {
  critical: "border-sz-crit/35 bg-sz-crit/10 text-sz-crit",
  elevated: "border-sz-elev/35 bg-sz-elev/10 text-sz-elev",
  normal: "border-sz-norm/40 bg-sz-norm/10 text-sz-norm",
};

export const CATEGORY_ELEMENT: Record<Category, string> = {
  flood: "text-sz-water",
  fire: "text-sz-crit",
  medical: "text-sz-crit",
  trapped: "text-sz-elev",
  structural: "text-sz-elev",
  other: "text-sz-norm",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  flood: "Flood",
  fire: "Fire",
  medical: "Medical",
  trapped: "Trapped",
  structural: "Structural",
  other: "Other",
};

export function isOfficialFirst(category: Category): boolean {
  return category === "fire" || category === "medical" || category === "structural";
}

export const DISPATCH_LABEL: Record<DispatchStatus, string> = {
  none: "Not sent",
  offered: "Offered",
  accepted: "Accepted",
  on_way: "On the way",
  arrived: "Arrived",
  confirmed: "Help confirmed",
  closed: "Closed",
  reopened: "Re-opened",
};

export const OFFER_LABEL: Record<OfferStatus, string> = {
  offered: "Offered",
  accepted: "Accepted",
  on_way: "On the way",
  arrived: "Arrived",
  done: "Done",
  declined: "Declined",
  expired: "No answer",
};

type Tone = "live" | "good" | "warn" | "idle" | "dim";

const TONE: Record<Tone, string> = {
  live: "border-sz-water/35 bg-sz-water/10 text-sz-water",
  good: "border-sz-earth/35 bg-sz-earth/10 text-sz-earth",
  warn: "border-sz-elev/35 bg-sz-elev/10 text-sz-elev",
  idle: "border-sz-line bg-sz-raised text-sz-text-2",
  dim: "border-sz-line bg-sz-base text-sz-text-3",
};

export function dispatchTone(status: DispatchStatus): string {
  switch (status) {
    case "accepted":
    case "on_way":
      return TONE.live;
    case "arrived":
    case "confirmed":
      return TONE.good;
    case "closed":
      return TONE.dim;
    case "reopened":
      return TONE.warn;
    case "offered":
      return TONE.idle;
    default:
      return TONE.dim;
  }
}

export function offerTone(status: OfferStatus): string {
  switch (status) {
    case "accepted":
    case "on_way":
      return TONE.live;
    case "arrived":
    case "done":
      return TONE.good;
    case "declined":
    case "expired":
      return TONE.dim;
    default:
      return TONE.idle;
  }
}

export function protocolLabels(path: ProtocolNode[] | null | undefined): string[] {
  if (!Array.isArray(path)) return [];
  return path
    .map((node) => {
      if (typeof node === "string") return node;
      if (node && typeof node === "object") {
        return node.label ?? node.id ?? node.node ?? "";
      }
      return "";
    })
    .filter((label): label is string => label.length > 0);
}
