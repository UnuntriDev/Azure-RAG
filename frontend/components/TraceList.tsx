"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, Bot, Loader2, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type { TraceSpan } from "@/types/api";

// Span name → bar colour (Tailwind classes). Tools share one colour, phases another.
function spanColor(name: string): string {
  if (name.startsWith("tool:")) return "bg-amber-400/70";
  if (name === "retrieval") return "bg-sky-400/70";
  if (name === "generation") return "bg-emerald-400/70";
  if (name === "agent") return "bg-primary/60";
  return "bg-white/30";
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "medium" });
}

function metaSummary(meta: Record<string, unknown>): string {
  const parts = Object.entries(meta).map(([k, v]) => `${k}: ${v}`);
  return parts.join(" · ");
}

function SpanBar({ span, total }: { span: TraceSpan; total: number }) {
  const pct = total > 0 ? Math.max(2, (span.duration_ms / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-44 shrink-0 truncate font-mono text-muted-foreground" title={span.name}>
        {span.name}
      </span>
      <div className="h-3 flex-1 overflow-hidden rounded bg-white/5">
        <div className={`h-full ${spanColor(span.name)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 shrink-0 text-right tabular-nums text-muted-foreground">
        {span.duration_ms} ms
      </span>
    </div>
  );
}

export function TraceList() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["traces"],
    queryFn: api.listTraces,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Wczytywanie…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/40 p-4 text-sm text-destructive">
        <AlertCircle className="size-4" />
        {error instanceof ApiError ? error.message : "Nie udało się pobrać śladów."}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-white/10 p-12 text-center text-muted-foreground">
        <Activity className="size-8" />
        <p>Brak śladów — zadaj pytanie w zakładce Asystent.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {data.map((t) => (
        <li key={t.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              {t.kind === "agent" ? (
                <Bot className="size-4 shrink-0 text-primary" />
              ) : (
                <Search className="size-4 shrink-0 text-sky-400" />
              )}
              <span className="truncate text-sm font-medium text-foreground">{t.question}</span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge variant="secondary">{t.kind}</Badge>
              <Badge variant="secondary">{t.prompt_version}</Badge>
              <span className="text-xs tabular-nums text-muted-foreground">{t.total_ms} ms</span>
            </div>
          </div>

          <div className="space-y-1.5">
            {t.spans.map((s, i) => (
              <div key={i}>
                <SpanBar span={s} total={t.total_ms} />
                {Object.keys(s.meta).length > 0 && (
                  <p className="ml-44 pl-3 text-[11px] text-muted-foreground/70">
                    {metaSummary(s.meta)}
                  </p>
                )}
              </div>
            ))}
          </div>

          <p className="mt-3 text-[11px] text-muted-foreground/60">{fmtTime(t.created_at)}</p>
        </li>
      ))}
    </ul>
  );
}
