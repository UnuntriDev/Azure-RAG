"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquare, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ConversationHistoryProps {
  open: boolean;
  onClose: () => void;
  currentId: string | null;
  onSelect: (id: string) => void;
  onDeleted: (id: string) => void;
}

export function ConversationHistory({
  open,
  onClose,
  currentId,
  onSelect,
  onDeleted,
}: ConversationHistoryProps) {
  const queryClient = useQueryClient();

  // Only fetch while the drawer is open — no need to poll a hidden panel.
  const { data: conversations, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
    enabled: open,
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      onDeleted(id);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Nie udało się usunąć rozmowy."),
  });

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden={!open}
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity duration-200",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      {/* Drawer */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-80 max-w-[85vw] flex-col border-r border-white/10 bg-card/95 backdrop-blur-xl transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Historia rozmów</h2>
          <button
            type="button"
            aria-label="Zamknij historię"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Wczytywanie…
            </div>
          ) : !conversations || conversations.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              Brak zapisanych rozmów.
            </p>
          ) : (
            <ul className="space-y-1">
              {conversations.map((c) => (
                <li key={c.id}>
                  <div
                    className={cn(
                      "group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                      c.id === currentId
                        ? "bg-white/10 text-foreground"
                        : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(c.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    >
                      <MessageSquare className="size-4 shrink-0" />
                      <span className="truncate">{c.title || "Bez tytułu"}</span>
                    </button>
                    <button
                      type="button"
                      aria-label="Usuń rozmowę"
                      onClick={() => del.mutate(c.id)}
                      disabled={del.isPending}
                      className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
