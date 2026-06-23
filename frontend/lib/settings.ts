import { useCallback, useEffect, useState } from "react";

export interface AppSettings {
  defaultChatMode: "agent" | "rag";
}

const DEFAULTS: AppSettings = {
  defaultChatMode: "agent",
};

const STORAGE_KEY = "rag-app-settings";

function loadSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

function saveSettings(s: AppSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {}
}

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULTS);

  // Hydrate from localStorage after mount (avoids SSR mismatch).
  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const update = useCallback(
    <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value };
        saveSettings(next);
        return next;
      });
    },
    [],
  );

  return { settings, update };
}
