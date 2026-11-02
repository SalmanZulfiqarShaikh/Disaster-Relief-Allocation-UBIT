import { useCallback, useEffect, useMemo, useState } from "react";

import * as api from "../lib/api";
import type {
  AdminStatus,
  CaseDetail,
  Channel,
  Volunteer,
} from "../lib/types";

export type DataSource = "loading" | "live" | "error";

interface DashboardState {
  cases: CaseDetail[];
  volunteers: Volunteer[];
  admin: AdminStatus | null;
  source: DataSource;

  error: string | null;

  unauthorized: boolean;
  streaming: boolean;
  loading: boolean;
  selectedId: number | null;
  selected: CaseDetail | null;
  select: (id: number) => void;
  approve: (id: number, channel: Channel) => Promise<void>;
  reopen: (id: number) => Promise<void>;
  toggleKillSwitch: () => Promise<void>;
  reload: () => void;
  busyCaseId: number | null;
  lastEvent: string | null;
}

const DETAIL_PREFETCH = 12;

export function useDashboard(): DashboardState {
  const [cases, setCases] = useState<CaseDetail[]>([]);
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [admin, setAdmin] = useState<AdminStatus | null>(null);
  const [source, setSource] = useState<DataSource>("loading");
  const [error, setError] = useState<string | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [busyCaseId, setBusyCaseId] = useState<number | null>(null);
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => setReloadToken((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const [rows, vols, status] = await Promise.all([
          api.listCases(),
          api.listVolunteers(),
          api.getAdminStatus(),
        ]);
        if (cancelled) return;

        const details = await Promise.all(
          rows.slice(0, DETAIL_PREFETCH).map(async (row) => {
            try {
              return await api.getCase(row.id);
            } catch {

              return { ...row, dispatches: [], events: [], responder_links: [] } as CaseDetail;
            }
          }),
        );
        if (cancelled) return;

        setCases(details);
        setVolunteers(vols);
        setAdmin(status);
        setError(null);
        setUnauthorized(false);
        setSource("live");
      } catch (caught) {
        if (cancelled) return;

        if (caught instanceof api.ApiError && caught.status === 401) {
          setUnauthorized(true);
          setError("Your session has ended. Sign in again.");
        } else {
          setError(
            caught instanceof api.ApiError
              ? `The backend answered ${caught.status}: ${caught.message}`
              : "Could not reach the backend. Is the server running?",
          );
        }
        setCases([]);
        setVolunteers([]);
        setAdmin(null);
        setSource("error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  useEffect(() => {
    if (source !== "live") return undefined;

    const close = api.openEventStream({
      onOpen: () => setStreaming(true),
      onError: () => setStreaming(false),
      onEvent: (payload) => {
        setLastEvent(typeof payload.type === "string" ? payload.type : null);
        const caseId = Number(payload.case_id);
        if (!Number.isFinite(caseId)) return;
        api
          .getCase(caseId)
          .then((fresh) => {
            setCases((prev) => {
              const without = prev.filter((row) => row.id !== fresh.id);
              return [...without, fresh].sort(
                (a, b) => b.priority_score - a.priority_score,
              );
            });
          })
          .catch(() => {
            /* the next event will bring it */
          });
      },
    });

    return close;
  }, [source]);

  const select = useCallback((id: number) => setSelectedId(id), []);

  const refreshCase = useCallback(async (id: number) => {
    try {
      const fresh = await api.getCase(id);
      setCases((prev) => prev.map((row) => (row.id === id ? fresh : row)));
    } catch {
      /* the stream will catch up */
    }
  }, []);

  const approve = useCallback(
    async (id: number, channel: Channel) => {
      setBusyCaseId(id);
      try {
        const result = await api.approveCase(id, channel);
        await refreshCase(id);

        setError(result.dispatch_warning ?? null);
      } catch (caught) {
        if (caught instanceof api.ApiError && caught.status === 401) {
          setUnauthorized(true);
        } else {
          setError(
            caught instanceof api.ApiError
              ? caught.message
              : "Could not reach the backend to approve that case.",
          );
        }
      } finally {
        setBusyCaseId(null);
      }
    },
    [refreshCase],
  );

  const reopen = useCallback(
    async (id: number) => {
      setBusyCaseId(id);
      try {
        await api.reopenCase(id, "Manual re-open by coordinator");
        await refreshCase(id);
      } catch (caught) {
        if (caught instanceof api.ApiError && caught.status === 401) {
          setUnauthorized(true);
        } else {
          setError(
            caught instanceof api.ApiError
              ? caught.message
              : "Could not reach the backend to re-open that case.",
          );
        }
      } finally {
        setBusyCaseId(null);
      }
    },
    [refreshCase],
  );

  const toggleKillSwitch = useCallback(async () => {
    if (!admin) return;

    const next = !admin.kill_switch;

    setAdmin((prev) => (prev ? { ...prev, kill_switch: next } : prev));

    try {
      const result = await api.setKillSwitch(next);
      setAdmin((prev) => (prev ? { ...prev, kill_switch: result.kill_switch } : prev));
    } catch {
      setAdmin((prev) => (prev ? { ...prev, kill_switch: !next } : prev));
      setError("Could not reach the backend. Outbound messages are unchanged.");
    }
  }, [admin]);

  const ranked = useMemo(
    () => [...cases].sort((a, b) => b.priority_score - a.priority_score),
    [cases],
  );

  const selected = useMemo(
    () => ranked.find((row) => row.id === selectedId) ?? ranked[0] ?? null,
    [ranked, selectedId],
  );

  return {
    cases: ranked,
    volunteers,
    admin,
    source,
    error,
    unauthorized,
    streaming,
    loading,
    selectedId: selected?.id ?? null,
    selected,
    select,
    approve,
    reopen,
    toggleKillSwitch,
    reload,
    busyCaseId,
    lastEvent,
  };
}
