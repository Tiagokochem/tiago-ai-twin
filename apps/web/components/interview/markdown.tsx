"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Props {
  content: string;
  citations: Citation[];
  onCite?: (n: number) => void;
  activeCite?: number | null;
}

const MARKER = /\[(\d{1,2})\](?!\()/g;

export function AnswerMarkdown({ content, citations, onCite, activeCite }: Props) {
  const linked = content.replace(MARKER, "[$1](#cite-$1)");
  return (
    <div className="prose-chat text-[15px] text-mist-100">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            if (href?.startsWith("#cite-")) {
              const n = Number(href.slice(6));
              const citation = citations.find((c) => c.n === n);
              return (
                <button
                  type="button"
                  onClick={() => onCite?.(n)}
                  title={citation ? `${citation.title} › ${citation.heading}` : undefined}
                  className={cn(
                    "mx-0.5 inline-grid h-[18px] min-w-[18px] -translate-y-0.5 place-items-center rounded-md px-1 align-middle font-mono text-[10px] font-semibold no-underline transition",
                    activeCite === n
                      ? "bg-cyan-glow text-ink-950"
                      : "bg-iris-500/25 text-iris-300 hover:bg-iris-500/45 hover:text-white",
                  )}
                >
                  {n}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {linked}
      </ReactMarkdown>
    </div>
  );
}
