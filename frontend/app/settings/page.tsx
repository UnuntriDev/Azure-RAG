"use client";

import { Bot, LogOut, MessageSquare } from "lucide-react";
import { useAuthContext } from "@/app/providers";
import { AUTH_ENABLED } from "@/lib/auth";
import { useSettings } from "@/lib/settings";
import { cn, getInitials } from "@/lib/utils";

export default function SettingsPage() {
  const { user, logout } = useAuthContext();
  const { settings, update } = useSettings();

  return (
    <div className="mx-auto max-w-xl space-y-6 py-2">
      <h1 className="text-xl font-semibold text-gray-100">Ustawienia</h1>

      {/* ── Account card ── */}
      {AUTH_ENABLED && user && (
        <section className="rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-md">
          <h2 className="mb-4 text-xs font-bold uppercase tracking-widest text-gray-300">
            Konto
          </h2>

          <div className="flex items-center justify-between gap-4">
            {/* Avatar + info */}
            <div className="flex min-w-0 items-center gap-4">
              <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-sky-500/20 text-lg font-bold text-sky-400 ring-1 ring-sky-500/30">
                {getInitials(user.name)}
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold text-gray-100">{user.name}</p>
                <p className="truncate text-sm text-gray-400">{user.email}</p>
                <p className="mt-1 text-xs text-gray-400">Zalogowano przez Google</p>
              </div>
            </div>

            {/* Logout button */}
            <button
              type="button"
              onClick={logout}
              className="flex shrink-0 items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-sm text-gray-300 transition-all duration-200 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400"
            >
              <LogOut className="size-4" />
              <span>Wyloguj się</span>
            </button>
          </div>
        </section>
      )}

      {/* ── Chat preferences card ── */}
      <section className="rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-md">
        <h2 className="mb-1 text-xs font-bold uppercase tracking-widest text-gray-300">
          Preferencje czatu
        </h2>
        <p className="mb-4 text-xs text-gray-400">
          Domyślny tryb przy otwieraniu nowej rozmowy. Można zmienić w trakcie czatu.
        </p>

        <div className="flex gap-3">
          <ModeButton
            active={settings.defaultChatMode === "agent"}
            icon={<Bot className="size-4" />}
            label="Tryb agenta"
            description="Model sam wybiera narzędzia: wyszukiwanie, porównanie, kalkulator."
            onClick={() => update("defaultChatMode", "agent")}
          />
          <ModeButton
            active={settings.defaultChatMode === "rag"}
            icon={<MessageSquare className="size-4" />}
            label="Tryb RAG"
            description="Bezpośrednie wyszukiwanie hybrydowe bez pośrednictwa agenta."
            onClick={() => update("defaultChatMode", "rag")}
          />
        </div>
      </section>
    </div>
  );
}

function ModeButton({
  active,
  icon,
  label,
  description,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 flex-col gap-1.5 rounded-lg border p-4 text-left transition-all duration-200",
        active
          ? "border-sky-500/50 bg-sky-500/10 text-sky-400"
          : "border-white/10 bg-white/3 text-gray-300 hover:border-white/25 hover:bg-white/8 hover:text-gray-100",
      )}
    >
      <span className="flex items-center gap-2 text-sm font-semibold">
        {icon}
        {label}
      </span>
      <span className={cn("text-xs leading-relaxed", active ? "text-sky-400/70" : "text-gray-400")}>
        {description}
      </span>
    </button>
  );
}
