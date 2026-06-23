"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, HelpCircle, Loader2, Sparkles, Tag, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";

interface DocumentAnalysisDialogProps {
  documentId: string;
  filename: string;
  onClose: () => void;
}

export function DocumentAnalysisDialog({
  documentId,
  filename,
  onClose,
}: DocumentAnalysisDialogProps) {
  // Analysis is an LLM call — cache per document so reopening doesn't re-run it.
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analysis", documentId],
    queryFn: () => api.analyzeDocument(documentId),
    staleTime: Infinity,
    retry: false,
  });

  return (
    <>
      <div
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        aria-hidden
      />
      <div className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border border-white/10 bg-card shadow-card">
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 shrink-0 text-primary" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Analiza dokumentu</h2>
              <p className="truncate text-xs text-muted-foreground">{filename}</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Zamknij"
            onClick={onClose}
            className="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Analizuję dokument…
            </div>
          ) : isError ? (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/40 p-4 text-sm text-destructive">
              <AlertCircle className="size-4 shrink-0" />
              {error instanceof ApiError ? error.message : "Nie udało się przeanalizować dokumentu."}
            </div>
          ) : data ? (
            <div className="space-y-5 text-sm">
              <section>
                <h3 className="mb-1 font-medium text-foreground">Streszczenie</h3>
                <p className="leading-relaxed text-muted-foreground">{data.summary}</p>
              </section>

              <section>
                <h3 className="mb-2 font-medium text-foreground">Kluczowe punkty</h3>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {data.key_points.map((point, i) => (
                    <li key={i}>{point}</li>
                  ))}
                </ul>
              </section>

              {data.entities.length > 0 && (
                <section>
                  <h3 className="mb-2 flex items-center gap-1.5 font-medium text-foreground">
                    <Tag className="size-4" /> Encje
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {data.entities.map((e, i) => (
                      <Badge key={i} variant="secondary" title={e.type}>
                        {e.name}
                        <span className="ml-1 text-muted-foreground">· {e.type}</span>
                      </Badge>
                    ))}
                  </div>
                </section>
              )}

              <section>
                <h3 className="mb-2 flex items-center gap-1.5 font-medium text-foreground">
                  <HelpCircle className="size-4" /> Sugerowane pytania
                </h3>
                <ul className="space-y-1 text-muted-foreground">
                  {data.suggested_questions.map((q, i) => (
                    <li key={i}>• {q}</li>
                  ))}
                </ul>
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
