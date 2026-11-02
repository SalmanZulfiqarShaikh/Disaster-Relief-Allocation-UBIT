import { useCallback, useEffect, useState } from "react";

import * as api from "../lib/api";

export type AuthState = "checking" | "in" | "out";

interface Auth {
  state: AuthState;
  email: string | null;

  configured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;

  refresh: () => void;
}

export function useAuth(): Auth {
  const [state, setState] = useState<AuthState>("checking");
  const [email, setEmail] = useState<string | null>(null);
  const [configured, setConfigured] = useState(true);
  const [token, setToken] = useState(0);

  const refresh = useCallback(() => setToken((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;

    api
      .me()
      .then((body) => {
        if (cancelled) return;
        setEmail(body.email);
        setConfigured(body.configured);
        setState(body.authenticated ? "in" : "out");
      })
      .catch(() => {

        if (!cancelled) setState("out");
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const signIn = useCallback(async (address: string, password: string) => {
    const body = await api.login(address, password);
    setEmail(body.email);
    setState("in");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {

      setEmail(null);
      setState("out");
    }
  }, []);

  return { state, email, configured, signIn, signOut, refresh };
}
