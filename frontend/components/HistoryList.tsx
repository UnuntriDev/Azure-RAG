"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquare, Trash2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";

export function HistoryList() {
  const queryClient = useQueryClient();

  const { data: conversations, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Nie udało się usunąć rozmowy."),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Wczytywanie…
      </div>
    );
  }

  if (!conversations || conversations.length === 0) {
    return (
      <p className="py-16 text-center text-sm text-muted-foreground">
        Brak zapisanych rozmów. Zacznij pytać w zakładce{" "}
        <Link href="/" className="text-primary hover:underline">
          Asystent
        </Link>
        .
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {conversations.map((c) => (
        <li
          key={c.id}
          className="group flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 transition-colors hover:bg-white/10"
        >
          <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate text-sm text-foreground">
            {c.title || "Bez tytułu"}
          </span>
          <span className="shrink-0 text-xs text-muted-foreground">
            {new Date(c.updated_at).toLocaleDateString("pl-PL", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          <Link
            href={`/?conv=${c.id}`}
            className="shrink-0 rounded-lg border border-white/10 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
          >
            Otwórz
          </Link>
          <button
            type="button"
            aria-label="Usuń rozmowę"
            onClick={() => del.mutate(c.id)}
            disabled={del.isPending}
            className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100 disabled:opacity-50"
          >
            <Trash2 className="size-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
