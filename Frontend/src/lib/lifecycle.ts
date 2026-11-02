

import type { CaseDetail, Stage } from "./types";

export const STAGES: readonly Stage[] = [
  "received",
  "triaging",
  "dispatched",
  "resolved",
] as const;

export const STAGE_LABEL: Record<Stage, string> = {
  received: "WhatsApp received",
  triaging: "Triaging priority",
  dispatched: "Resource dispatched",
  resolved: "Status resolved",
};

export const STAGE_SHORT: Record<Stage, string> = {
  received: "Received",
  triaging: "Triaging",
  dispatched: "Dispatched",
  resolved: "Resolved",
};

const DISPATCHED: ReadonlySet<string> = new Set([
  "offered",
  "accepted",
  "on_way",
  "arrived",
]);

const FINISHED: ReadonlySet<string> = new Set(["confirmed", "closed"]);

export function stageOf(row: CaseDetail): Stage {
  if (row.ui_stage) return row.ui_stage;
  if (row.status === "resolved" || FINISHED.has(row.dispatch_status)) return "resolved";
  if (DISPATCHED.has(row.dispatch_status)) return "dispatched";
  if (row.status === "proposed" || row.status === "approved") return "triaging";
  return "received";
}

export function stageIndex(stage: Stage): number {
  return STAGES.indexOf(stage);
}

export function isStageComplete(row: CaseDetail, stage: Stage): boolean {
  if (row.reopened && stage === "resolved") return false;
  return stageIndex(stage) < stageIndex(stageOf(row));
}

export function awaitingDispatch(row: CaseDetail): boolean {
  if (stageOf(row) !== "triaging" && !row.reopened) return false;

  if (row.priority_score <= 0) return false;
  if (row.dispatch_status !== "none" && !row.reopened) return false;
  const incident = row.incident;

  return Boolean(incident && (incident.location_source === "pin" || incident.location_known));
}
