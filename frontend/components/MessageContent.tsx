"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Source } from "@/types/api";
import type { ComponentPropsWithoutRef } from "react";

// Matches [1], [2, 3], [plik.pdf, s. 1], [doc.xlsx, chunk 3] etc.
const CITATION_RE = /\s*\[(?:\d+(?:,\s*\d+)*|[^\]]*\.[a-zA-Z]{2,5}[^\]]*)\]/g;

function findSourceIndex(inner: string, sources: Source[]): number {
  // Filename + location match
  for (let i = 0; i < sources.length; i++) {
    if (inner.includes(sources[i].filename) && inner.includes(sources[i].location)) {
      return i;
    }
  }
  // Filename-only match
  for (let i = 0; i < sources.length; i++) {
    if (inner.includes(sources[i].filename)) {
      return i;
    }
  }
  return -1;
}

function processCitations(text: string, sources: Source[]): string {
  return text.replace(CITATION_RE, (match) => {
    const trimmed = match.trimStart();
    const space = match.length > trimmed.length ? " " : "";
    const inner = trimmed.slice(1, -1);

    // Numeric: [1], [2, 3]
    if (/^\d+(?:,\s*\d+)*$/.test(inner)) {
      return (
        space +
        inner
          .split(",")
          .map((n) => {
            const idx = parseInt(n.trim()) - 1;
            return idx >= 0 && idx < sources.length
              ? `[${idx + 1}](#cite:${idx})`
              : `[${idx + 1}]`;
          })
          .join(" ")
      );
    }

    // File-based: [report.pdf, s. 3] → render as [1]
    const idx = findSourceIndex(inner, sources);
    if (idx >= 0) return `${space}[${idx + 1}](#cite:${idx})`;
    return match;
  });
}

interface Props {
  content: string;
  sources?: Source[] | null;
  streaming?: boolean;
  onCiteClick?: (sourceIndex: number) => void;
}

export function MessageContent({ content, sources, streaming, onCiteClick }: Props) {
  const processed = sources?.length ? processCitations(content, sources) : content;

  return (
    <div className="prose-invert prose-sm max-w-none leading-relaxed text-foreground">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...rest }: ComponentPropsWithoutRef<"a">) {
            if (typeof href === "string" && href.startsWith("#cite:")) {
              const idx = parseInt(href.slice(6));
              return (
                <button
                  type="button"
                  onClick={() => onCiteClick?.(idx)}
                  className="mx-0.5 inline-flex items-center rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
                >
                  {children}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline" {...rest}>
                {children}
              </a>
            );
          },
          code({ className, children, ...rest }) {
            const match = /language-(\w+)/.exec(className || "");
            const code = String(children).replace(/\n$/, "");
            if (match) {
              return (
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{ margin: "0.75rem 0", borderRadius: "0.5rem", fontSize: "0.8rem" }}
                >
                  {code}
                </SyntaxHighlighter>
              );
            }
            return (
              <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs" {...rest}>
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-lg border border-white/10">
                <table className="min-w-full text-sm">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return <th className="border-b border-white/10 bg-white/5 px-3 py-2 text-left font-medium">{children}</th>;
          },
          td({ children }) {
            return <td className="border-b border-white/5 px-3 py-2">{children}</td>;
          },
          ul({ children }) {
            return <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>;
          },
          p({ children }) {
            return <p className="my-2 first:mt-0 last:mb-0">{children}</p>;
          },
          blockquote({ children }) {
            return <blockquote className="my-2 border-l-2 border-primary/50 pl-3 italic text-muted-foreground">{children}</blockquote>;
          },
        }}
      >
        {processed}
      </ReactMarkdown>
      {streaming && (
        <span className="ml-1 inline-block size-2 animate-pulse rounded-full bg-primary" />
      )}
    </div>
  );
}
