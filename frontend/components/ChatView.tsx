"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUp,
  Bot,
  CalendarSearch,
  Check,
  FileText,
  ListChecks,
  Loader2,
  PanelLeft,
  Plus,
  Sparkles,
  TriangleAlert,
  Wrench,
  X,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSettings } from "@/lib/settings";
import { toast } from "sonner";

import { ConversationHistory } from "@/components/ConversationHistory";
import { MessageContent } from "@/components/MessageContent";
import { SourcesList } from "@/components/SourcesList";
import { api, ApiError } from "@/lib/api";
import type { Source } from "@/types/api";

const MAX_MB = 50;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".csv"];
const ACCEPT =
  ".pdf,.docx,.xlsx,.csv,application/pdf," +
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document," +
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";

const QUICK_PROMPTS = [
  { icon: ListChecks, label: "Najważniejsze fakty", prompt: "Wypisz najważniejsze fakty z dokumentu." },
  { icon: FileText, label: "Streść dokument", prompt: "Streść dokument w kilku zdaniach." },
  { icon: CalendarSearch, label: "Znajdź datę", prompt: "Jakie daty pojawiają się w dokumencie?" },
  { icon: Sparkles, label: "O czym to jest?", prompt: "O czym jest ten dokument?" },
];

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext)))
    return "Dozwolone formaty: PDF, Word (.docx), Excel (.xlsx), CSV.";
  if (file.size > MAX_MB * 1024 * 1024) return `Maksymalny rozmiar to ${MAX_MB} MB.`;
  return null;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[] | null;
  latencyMs?: number | null;
  streaming?: boolean;
  toolActivity?: string | null; // friendly label of the tool the agent is currently running
}

const TOOL_LABELS: Record<string, string> = {
  search_documents: "Przeszukuję dokumenty…",
  compare_documents: "Porównuję dokumenty…",
  calculator: "Liczę…",
};

export function ChatView() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [question, setQuestion] = useState("");
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [attachedIds, setAttachedIds] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [highlightedCites, setHighlightedCites] = useState<Record<string, number | null>>({});
  const { settings } = useSettings();
  const [agentMode, setAgentMode] = useState(true);

  // Sync with user's saved preference on first load.
  useEffect(() => {
    setAgentMode(settings.defaultChatMode === "agent");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.defaultChatMode]);
  const [promptVersion, setPromptVersion] = useState("v1");

  const { data: docs } = useQuery({
    queryKey: ["documents"],
    queryFn: api.listDocuments,
    refetchInterval: (q) =>
      q.state.data?.some((d) => d.status === "pending" || d.status === "processing") ? 2000 : false,
  });

  const { data: promptVersions } = useQuery({
    queryKey: ["prompt-versions"],
    queryFn: api.listPromptVersions,
    staleTime: Infinity,
    placeholderData: [
      { id: "v1", label: "Standardowy", description: "Pełne, rzeczowe odpowiedzi", default: true },
      { id: "v2", label: "Zwięzły", description: "Krótkie odpowiedzi — tylko sedno", default: false },
    ],
  });

  const indexedCount = docs?.filter((d) => d.status === "indexed").length ?? 0;
  const noIndexedDocs = docs !== undefined && indexedCount === 0;
  const attached = attachedIds
    .map((id) => docs?.find((d) => d.id === id))
    .filter((d): d is NonNullable<typeof d> => Boolean(d));

  // When files are attached, the query is scoped to *them* — so we must gate on whether the
  // attached files are indexed, not on the whole corpus. Otherwise a query against a still-
  // indexing attachment returns nothing (or, pre-filter, leaked other docs).
  const attachedIndexed = attached.filter((d) => d.status === "indexed");
  const attachmentsPending = attachedIds.length > 0 && attachedIndexed.length === 0;
  const cannotSubmit = attachmentsPending || (attachedIds.length === 0 && noIndexedDocs);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load conversation from URL param (?conv=<id>) — set by the Historia page "Otwórz" links.
  useEffect(() => {
    const convParam = searchParams.get("conv");
    if (!convParam || convParam === conversationId) return;
    loadConversation(convParam).then(() => {
      // Strip the param so Back/refresh doesn't re-load unexpectedly.
      router.replace("/");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function handleUpload(file: File) {
    const error = validateFile(file);
    if (error) {
      toast.error(error);
      return;
    }
    setUploading(true);
    setProgress(0);
    try {
      const doc = await api.uploadDocument(file, setProgress);
      toast.success(`Wgrano „${doc.filename}" — indeksowanie w toku.`);
      setAttachedIds((prev) => [...prev, doc.id]);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Nie udało się wgrać pliku.");
    } finally {
      setUploading(false);
    }
  }

  async function submit() {
    const q = question.trim();
    if (!q || isStreaming || cannotSubmit) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: q };
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setQuestion("");
    setIsStreaming(true);

    await api.chatStream(
      {
        question: q,
        conversation_id: conversationId,
        agent: agentMode,
        prompt_version: promptVersion,
        document_ids: attachedIds.length > 0 ? attachedIds : null,
      },
      {
        onConversationId: (id) => {
          setConversationId(id);
          // New conversation just got an id → refresh the history list.
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
        },
        onTool: (name) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                toolActivity: TOOL_LABELS[name] ?? `Używam: ${name}…`,
              };
            }
            return updated;
          });
        },
        onDelta: (content) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              // First token arriving means the tool phase is over — clear the activity line.
              updated[updated.length - 1] = {
                ...last,
                content: last.content + content,
                toolActivity: null,
              };
            }
            return updated;
          });
        },
        onSources: (sources) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              updated[updated.length - 1] = { ...last, sources };
            }
            return updated;
          });
        },
        onDone: (latencyMs) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                streaming: false,
                latencyMs,
                toolActivity: null,
              };
            }
            return updated;
          });
          setIsStreaming(false);
        },
        onError: (detail) => {
          toast.error(detail);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant" && last.streaming) {
              updated[updated.length - 1] = {
                ...last,
                content: last.content || "Wystąpił błąd.",
                streaming: false,
              };
            }
            return updated;
          });
          setIsStreaming(false);
        },
      },
    );
  }

  function newChat() {
    setConversationId(null);
    setMessages([]);
    setAttachedIds([]);
  }

  async function loadConversation(id: string) {
    if (id === conversationId) {
      setHistoryOpen(false);
      return;
    }
    setLoadingConv(true);
    try {
      const conv = await api.getConversation(id);
      setMessages(
        conv.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources,
          latencyMs: m.latency_ms,
        })),
      );
      setConversationId(conv.id);
      setAttachedIds([]);
      setHistoryOpen(false);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Nie udało się wczytać rozmowy.");
    } finally {
      setLoadingConv(false);
    }
  }

  function handleDeleted(id: string) {
    // If the open conversation was deleted, reset to a fresh chat.
    if (id === conversationId) newChat();
  }

  const hasMessages = messages.length > 0;

  const inputPanel = (
    <div className="w-full max-w-2xl space-y-4">
      {hasMessages && (
        <button
          type="button"
          onClick={newChat}
          className="mx-auto flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
        >
          <Plus className="size-3" />
          Nowa rozmowa
        </button>
      )}

      <div className="rounded-3xl border border-white/10 bg-white/5 p-3 shadow-card backdrop-blur-xl transition-colors focus-within:border-white/20 sm:p-4">
        {(attached.length > 0 || uploading) && (
          <div className="mb-2 flex flex-wrap gap-2 px-1">
            {attached.map((d) => (
              <span
                key={d.id}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-muted-foreground"
              >
                {d.status === "indexed" ? (
                  <Check className="size-3.5 text-emerald-400" />
                ) : d.status === "failed" ? (
                  <TriangleAlert className="size-3.5 text-destructive" />
                ) : (
                  <Loader2 className="size-3.5 animate-spin" />
                )}
                <span className="max-w-[14rem] truncate text-foreground/90">{d.filename}</span>
                <button
                  type="button"
                  aria-label={`Odepnij ${d.filename}`}
                  onClick={() => setAttachedIds((prev) => prev.filter((id) => id !== d.id))}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              </span>
            ))}
            {uploading && (
              <span className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Wgrywanie… {progress}%
              </span>
            )}
          </div>
        )}

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder={
            attachmentsPending
              ? "Podpięty dokument jeszcze się indeksuje…"
              : noIndexedDocs
                ? "Najpierw wgraj dokument (przycisk +)…"
                : "Zadaj pytanie o swoje dokumenty…"
          }
          className="max-h-48 w-full resize-none bg-transparent px-2 pt-1 text-foreground outline-none ring-0 placeholder:text-muted-foreground"
        />

        <div className="mt-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Wgraj plik"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 text-foreground transition-colors hover:bg-white/10 disabled:opacity-50"
            >
              {uploading ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
            </button>

            <button
              type="button"
              aria-pressed={agentMode}
              onClick={() => setAgentMode((v) => !v)}
              title={
                agentMode
                  ? "Tryb agenta: model sam wybiera narzędzia (wyszukiwanie, porównanie, kalkulator)"
                  : "Klasyczny RAG: jedno wyszukiwanie + odpowiedź"
              }
              className={
                "flex h-9 shrink-0 items-center gap-1.5 rounded-lg border px-3 text-sm transition-colors " +
                (agentMode
                  ? "border-primary/40 bg-primary/15 text-primary"
                  : "border-white/10 text-muted-foreground hover:bg-white/5 hover:text-foreground")
              }
            >
              <Bot className="size-4" />
              Agent
            </button>

            {promptVersions && promptVersions.length > 1 && (
              <>
              <div aria-hidden className="h-5 w-px bg-white/15" />
              <div className="flex h-9 shrink-0 items-center rounded-lg border border-white/10 bg-white/[0.03] p-0.5">
                {promptVersions.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPromptVersion(p.id)}
                    className={
                      "relative rounded-md px-3 py-1 text-sm transition-all duration-200 " +
                      (promptVersion === p.id
                        ? "bg-primary/20 font-semibold text-primary shadow-sm"
                        : "text-muted-foreground hover:text-foreground")
                    }
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              </>
            )}
          </div>

          <button
            type="button"
            aria-label="Wyślij"
            onClick={submit}
            disabled={!question.trim() || isStreaming || cannotSubmit}
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-foreground text-background transition-opacity hover:opacity-90 disabled:opacity-30"
          >
            {isStreaming ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
            e.target.value = "";
          }}
        />
      </div>

      {!hasMessages && (
        <div className="flex flex-wrap justify-center gap-2">
          {QUICK_PROMPTS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              type="button"
              onClick={() => setQuestion(prompt)}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
            >
              <Icon className="size-4" />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="flex min-h-[70vh] flex-col items-center py-8">
      <ConversationHistory
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        currentId={conversationId}
        onSelect={loadConversation}
        onDeleted={handleDeleted}
      />

      {/* History toggle — fixed top-left, below the header, available in both states. */}
      <button
        type="button"
        aria-label="Historia rozmów"
        onClick={() => setHistoryOpen(true)}
        className="fixed left-4 top-20 z-30 flex size-9 items-center justify-center rounded-lg border border-white/10 bg-card/80 text-muted-foreground backdrop-blur-sm transition-colors hover:bg-white/10 hover:text-foreground"
      >
        {loadingConv ? <Loader2 className="size-4 animate-spin" /> : <PanelLeft className="size-4" />}
      </button>

      {!hasMessages ? (
        /* Hero state: heading + input together, vertically centered */
        <div className="flex flex-1 flex-col items-center justify-center gap-16">
          <h1 className="-mt-[100px] text-center text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Wpisz pytanie, ja zajmę się resztą.
          </h1>
          {inputPanel}
        </div>
      ) : (
        /* Chat state: messages fill space, input pinned below */
        <>
          <div className="w-full max-w-2xl flex-1 space-y-6 pb-4">
            {messages.map((msg) => (
              <div key={msg.id}>
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl bg-white/10 px-4 py-3 text-foreground">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                        <Sparkles className="size-4 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1 space-y-3">
                        {msg.toolActivity && (
                          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-muted-foreground">
                            <Wrench className="size-3.5 animate-pulse text-primary" />
                            {msg.toolActivity}
                          </span>
                        )}
                        {(msg.content || !msg.toolActivity) && (
                          <MessageContent
                            content={msg.content}
                            sources={msg.sources}
                            streaming={msg.streaming}
                            onCiteClick={(idx) =>
                              setHighlightedCites((prev) => ({ ...prev, [msg.id]: idx }))
                            }
                          />
                        )}
                        {msg.latencyMs != null && (
                          <span className="text-xs text-muted-foreground">{msg.latencyMs} ms</span>
                        )}
                        {msg.sources && msg.sources.length > 0 && (
                          <SourcesList
                            sources={msg.sources}
                            highlightedIndex={highlightedCites[msg.id] ?? null}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          {inputPanel}
        </>
      )}
    </div>
  );
}
