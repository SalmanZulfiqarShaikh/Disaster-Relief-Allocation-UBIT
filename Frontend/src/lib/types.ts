

export type Category =
  | "flood"
  | "fire"
  | "medical"
  | "trapped"
  | "structural"
  | "other";

export type CaseStatus = "proposed" | "approved" | "rejected" | "resolved";

export type DispatchStatus =
  | "none"
  | "offered"
  | "accepted"
  | "on_way"
  | "arrived"
  | "confirmed"
  | "closed"
  | "reopened";

export type OfferStatus =
  | "offered"
  | "accepted"
  | "on_way"
  | "arrived"
  | "done"
  | "declined"
  | "expired";

export type VolunteerStatus = "off_duty" | "on_duty" | "busy";

export type RiskLevel = "normal" | "elevated" | "critical";

export type IncidentStatus = "open" | "active" | "resolved" | "closed";

export type LocationSource = "pin" | "area" | null;

export type Channel = "volunteers" | "responder" | "both";

export interface Zone {
  id: string;
  name: string;
  risk_level: RiskLevel | null;
  lat: number | null;
  lng: number | null;
  volunteer_group?: string | null;
}

export interface PersonVuln {
  elderly?: boolean;
  alone?: boolean;
  cannot_move?: boolean;
  children?: boolean;
  floor?: string;
  [key: string]: unknown;
}

export interface PersonBrief {
  id: number;
  first_name: string | null;
  person_vuln: PersonVuln;
}

export interface Incident {
  id: number;
  category: Category;
  lat: number | null;
  lng: number | null;
  zone_id: string | null;
  location_known: boolean;
  location_source?: LocationSource;
  report_count: number;
  confidence: number;
  urgency: number;
  priority_score: number;
  status: IncidentStatus;
  dispatch_status: DispatchStatus;
  reopened: boolean;
  reopen_reason: string | null;
  first_report_at: string;
  last_update_at: string;
}

export type ProtocolNode = string | { id?: string; label?: string; node?: string };

export interface VolunteerBrief {
  id: number;
  name: string | null;

  phone_masked: string;
  is_demo: boolean;
}

export interface DispatchRow {
  id: number;
  case_id: number;
  volunteer_id: number;
  ring: number;
  status: OfferStatus;
  offered_at: string | null;
  accepted_at: string | null;
  arrived_at: string | null;
  done_at: string | null;
  volunteer: VolunteerBrief;
}

export interface EventRow {
  id: number;
  type: string;
  case_id: number | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ResponderLinkRow {
  token: string;
  target_label: string | null;
  created_at: string;
  expires_at: string;
}

export interface CaseRow {
  id: number;
  incident_id: number | null;
  person_id: number | null;
  priority_score: number;
  reason: string | null;
  vuln_summary: string | null;
  protocol_path: ProtocolNode[];
  status: CaseStatus;
  dispatch_status: DispatchStatus;
  reopened: boolean;
  reopen_reason: string | null;
  created_at: string;
  closed_at: string | null;
  incident: Incident | null;
  person: PersonBrief | null;
  zone: Zone | null;
  dispatch_count: number;
}

export type Stage = "received" | "triaging" | "dispatched" | "resolved";

export interface CaseDetail extends CaseRow {
  responder_links: ResponderLinkRow[];
  dispatches: DispatchRow[];
  events: EventRow[];

  ui_stage?: Stage;

  simulated?: boolean;
}

export interface Volunteer {
  id: number;
  name: string | null;

  phone: string;
  status: VolunteerStatus;
  zone_ids: string[];
  capabilities: string[];
  lat: number | null;
  lng: number | null;
  is_demo: boolean;
}

export interface ResponderView {
  token: string;
  target_label: string | null;
  expires_at: string;
  case: {
    id: number;
    status: CaseStatus;
    dispatch_status: DispatchStatus;
    priority_score: number;
    reason: string | null;
    vuln_summary: string | null;
    protocol_path: ProtocolNode[];
    reopened: boolean;
    reopen_reason: string | null;
    created_at: string;
  };
  incident: {
    id: number;
    category: Category;
    urgency: number;
    confidence: number;
    location_known: boolean;
    lat: number | null;
    lng: number | null;
    area: string | null;
    status: IncidentStatus;
    dispatch_status: DispatchStatus;
    created_at: string;
    report_count: number;
  } | null;
  person: { first_name: string | null } | null;
  zone: Pick<Zone, "id" | "name" | "risk_level"> | null;

  call: { label: string; number: string | null };
}

export interface AdminStatus {
  kill_switch: boolean;
  mock_mode: boolean;
  demo_mode: boolean;
  allowlist_only: boolean;

  problems: string[];
}

export interface ApproveResult {
  case_id: number;
  status: "approved";
  channel: Channel;
  offered?: Array<{ id: number; name: string | null; phone_masked: string }>;
  dispatch_warning?: string;
  responder_link?: {
    token: string;
    url: string;
    expires_at: string;
    target_label: string | null;
  };
  official?: {
    required: boolean;
    label: string;
    service: string | null;
    target_label: string | null;
  };
  official_forced?: string;
}

export interface RegistrationResult {
  code: string;
  expires_at: string;
  whatsapp_url: string | null;
  instructions: string;
}

export interface RegistrationStatus {
  found: boolean;
  verified: boolean;
  first_name?: string | null;
  zone_id?: string | null;
}

export type ResourceKind = "shelter" | "medical" | "vehicle" | "relief";

export interface ResourceStat {
  kind: ResourceKind;
  label: string;
  available: number;
  deployed: number;

  simulated: boolean;
}
