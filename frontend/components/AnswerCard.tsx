"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { QueryResponse } from "@/types/api";

import { MessageContent } from "./MessageContent";
import { SourcesList } from "./SourcesList";

export function AnswerCard({ response }: { response: QueryResponse }) {
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Odpowiedź</span>
          <span className="text-xs font-normal text-muted-foreground">{response.latency_ms} ms</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <MessageContent
          content={response.answer}
          sources={response.sources}
          onCiteClick={setHighlightedIndex}
        />
        <SourcesList sources={response.sources} highlightedIndex={highlightedIndex} />
      </CardContent>
    </Card>
  );
}
