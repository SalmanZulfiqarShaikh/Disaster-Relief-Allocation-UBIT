

import type {
  AdminStatus,
  ApproveResult,
  CaseDetail,
  CaseRow,
  Channel,
  DispatchRow,
  RegistrationResult,
  RegistrationStatus,
  ResponderView,
  Volunteer,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,

    credentials: "include",
    ...init,
  });

  if (!response.ok) {

    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* not JSON — keep the status text */
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export const login = (email: string, password: string) =>
  request<{ email: string; expires_in: number }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const logout = () =>
  request<{ signed_out: boolean }>("/api/auth/logout", { method: "POST" });

export const me = () =>
  request<{ authenticated: boolean; email: string | null; configured: boolean }>(
    "/api/auth/me",
  );

export const getWhatsapp = () =>
  request<{
    configured: boolean;
    number: string | null;
    display: string | null;
    url: string | null;
  }>("/api/whatsapp");

export const listZones = () =>
  request<Array<{ id: string; name: string; lat: number | null; lng: number | null }>>(
    "/api/zones",
  );

export const listCases = () => request<CaseRow[]>("/api/cases");

export const getCase = (caseId: number) =>
  request<CaseDetail>(`/api/cases/${caseId}`);

export const listDispatches = (caseId: number) =>
  request<DispatchRow[]>(`/api/cases/${caseId}/dispatches`);

export const approveCase = (
  caseId: number,
  channel: Channel,
  targetLabel?: string,
) =>
  request<ApproveResult>(`/api/proposals/${caseId}/approve`, {
    method: "POST",
    body: JSON.stringify({ channel, target_label: targetLabel ?? null }),
  });

export const createResponderLink = (caseId: number, targetLabel?: string) =>
  request<{
    token: string;
    url: string;
    expires_at: string;
    target_label: string | null;
  }>(`/api/cases/${caseId}/responderlink`, {
    method: "POST",
    body: JSON.stringify({ target_label: targetLabel ?? null }),
  });

export const reopenCase = (caseId: number, reason: string, reoffer = true) =>
  request<{ case_id: number; reopened: boolean; reason: string; case: CaseRow }>(
    `/api/cases/${caseId}/reopen`,
    { method: "POST", body: JSON.stringify({ reason, reoffer }) },
  );

export const listVolunteers = () => request<Volunteer[]>("/api/volunteers");

export const getResponderView = (token: string) =>
  request<ResponderView>(`/api/r/${encodeURIComponent(token)}`);

export const getAdminStatus = () => request<AdminStatus>("/api/admin/status");

export const setKillSwitch = (enabled?: boolean) =>
  request<{ kill_switch: boolean }>("/api/admin/killswitch", {
    method: "POST",
    body: JSON.stringify({ enabled: enabled ?? null }),
  });

export const register = (
  firstName: string,
  zoneId: string | null,
  wantsAlerts = true,
) =>
  request<RegistrationResult>("/api/register", {
    method: "POST",
    body: JSON.stringify({
      first_name: firstName,
      zone_id: zoneId,
      wants_alerts: wantsAlerts,
    }),
  });

export const registrationStatus = (code: string) =>
  request<RegistrationStatus>(`/api/register/${encodeURIComponent(code)}`);

export interface StreamHandlers {
  onEvent: (payload: { type: string; [key: string]: unknown }) => void;
  onOpen?: () => void;
  onError?: () => void;
}

export function openEventStream({ onEvent, onOpen, onError }: StreamHandlers): () => void {
  if (typeof EventSource === "undefined") return () => {};

  const source = new EventSource(`${BASE}/events`);

  source.onopen = () => onOpen?.();
  source.onerror = () => onError?.();
  source.onmessage = (message) => {
    if (!message.data) return;
    try {
      onEvent(JSON.parse(message.data) as { type: string });
    } catch {
      /* A dropped or partial frame is an inconvenience, not data loss — the
         timeline rebuilds from the events table. */
    }
  };

  return () => source.close();
}
