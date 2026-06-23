"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, FileText, Loader2, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { DocumentAnalysisDialog } from "@/components/DocumentAnalysisDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import type { DocumentStatus } from "@/types/api";

const STATUS: Record<
  DocumentStatus,
  { label: string; className?: string; destructive?: boolean; spin?: boolean }
> = {
  pending: { label: "Oczekuje" },
  processing: { label: "Przetwarzanie", spin: true },
  indexed: { label: "Zaindeksowany", className: "bg-green-600 text-white hover:bg-green-600" },
  failed: { label: "Błąd", destructive: true },
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

export function DocumentList() {
  const queryClient = useQueryClient();
  const [analyzing, setAnalyzing] = useState<{ id: string; filename: string } | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["documents"],
    queryFn: api.listDocuments,
    // Poll every 2s while any job is in flight; stop once everything settled.
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.status === "pending" || d.status === "processing")
        ? 2000
        : false,
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      toast.success("Usunięto dokument.");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Nie udało się usunąć."),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/50 p-4 text-sm text-destructive">
        <AlertCircle className="size-4" />
        Nie udało się pobrać dokumentów{error instanceof ApiError ? `: ${error.message}` : "."}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-md border border-dashed p-10 text-center text-muted-foreground">
        <FileText className="size-8" />
        <p>Brak dokumentów — wgraj pierwszy PDF.</p>
      </div>
    );
  }

  return (
    <>
      {analyzing && (
        <DocumentAnalysisDialog
          documentId={analyzing.id}
          filename={analyzing.filename}
          onClose={() => setAnalyzing(null)}
        />
      )}
      <Table>
        <TableHeader>
        <TableRow>
          <TableHead>Plik</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Fragmenty</TableHead>
          <TableHead>Dodano</TableHead>
          <TableHead className="w-20" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((doc) => {
          const cfg = STATUS[doc.status];
          return (
            <TableRow key={doc.id}>
              <TableCell className="font-medium">{doc.filename}</TableCell>
              <TableCell>
                <Badge
                  variant={cfg.destructive ? "destructive" : "secondary"}
                  className={cfg.className}
                  title={doc.error_message ?? undefined}
                >
                  {cfg.spin && <Loader2 className="mr-1 size-3 animate-spin" />}
                  {cfg.label}
                </Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">{doc.chunk_count ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{fmtDate(doc.created_at)}</TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1">
                  {doc.status === "indexed" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Analizuj ${doc.filename}`}
                      title="Analiza dokumentu"
                      onClick={() => setAnalyzing({ id: doc.id, filename: doc.filename })}
                    >
                      <Sparkles className="size-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Usuń ${doc.filename}`}
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(doc.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
      </Table>
    </>
  );
}
