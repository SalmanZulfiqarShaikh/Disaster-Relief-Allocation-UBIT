import { useEffect, useState } from "react";

import * as api from "../lib/api";

export interface Whatsapp {

  url: string;

  number?: string;

  display?: string;
  loading: boolean;
}

export function useWhatsapp(): Whatsapp {
  const [state, setState] = useState<Whatsapp>({ url: "", loading: true });

  useEffect(() => {
    let cancelled = false;

    api
      .getWhatsapp()
      .then((body) => {
        if (cancelled) return;
        setState({
          url: body.url ?? "",
          number: body.number ?? undefined,
          display: body.display ?? undefined,
          loading: false,
        });
      })
      .catch(() => {

        if (!cancelled) setState({ url: "", loading: false });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
