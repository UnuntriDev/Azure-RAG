"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { Source } from "@/types/api";

interface Props {
  sources: Source[];
  highlightedIndex?: number | null;
}

export function SourcesList({ sources, highlightedIndex }: Props) {
  const [outerOpen, setOuterOpen] = useState(false);
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  useEffect(() => {
    if (highlightedIndex == null) return;
    setOuterOpen(true);
    setOpenItems((prev) => new Set([...prev, highlightedIndex]));
    requestAnimationFrame(() => {
      setTimeout(() => {
        itemRefs.current.get(highlightedIndex)?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 150);
    });
  }, [highlightedIndex]);

  if (sources.length === 0) return null;

  function toggleItem(idx: number) {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  return (
    <Collapsible open={outerOpen} onOpenChange={setOuterOpen} className="rounded-md border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium text-muted-foreground hover:bg-muted/50">
        <span>Źródła ({sources.length})</span>
        <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-2 px-3 pb-3">
        {sources.map((s, i) => {
          const isHighlighted = highlightedIndex === i;
          return (
            <Collapsible
              key={`${s.document_id}-${s.chunk_index}`}
              open={openItems.has(i)}
              onOpenChange={() => toggleItem(i)}
              className={
                "rounded-md border transition-colors duration-500" +
                (isHighlighted ? " border-primary/60 bg-primary/10 ring-1 ring-primary/30" : "")
              }
            >
              <div
                ref={(el) => {
                  if (el) itemRefs.current.set(i, el);
                  else itemRefs.current.delete(i);
                }}
              >
                <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-muted/50">
                  <span className="flex min-w-0 items-center gap-2">
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">
                      [{i + 1}] {s.filename}, {s.location}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Badge variant="secondary">score {s.score.toFixed(3)}</Badge>
                    <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
                  </span>
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent className="whitespace-pre-wrap border-t px-3 py-2 text-sm text-muted-foreground">
                {s.content}
              </CollapsibleContent>
            </Collapsible>
          );
        })}
      </CollapsibleContent>
    </Collapsible>
  );
}
