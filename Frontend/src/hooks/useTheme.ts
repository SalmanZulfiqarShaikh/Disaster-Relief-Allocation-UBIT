import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const KEY = "savezone-theme";

function readStored(): Theme {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* blocked or unavailable — fall through to the default */
  }
  return "light";
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(readStored);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* the choice just will not survive a reload */
    }
  }, [theme]);

  const toggle = useCallback(
    () => setTheme((current) => (current === "light" ? "dark" : "light")),
    [],
  );

  return { theme, toggle };
}
