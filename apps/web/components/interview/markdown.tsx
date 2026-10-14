"use client";

import { memo, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
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
const CITE_PREFIX = "#cite-";

/** Model output is untrusted: only https and mailto links are rendered as links. */
export function safeHref(href: string | undefined): string | null {
  if (!href) return null;
  if (href.startsWith(CITE_PREFIX)) return href;
  try {
    const url = new URL(href);
    return url.protocol === "https:" || url.protocol === "mailto:" ? url.href : null;
  } catch {
    return null;
  }
}

function AnswerMarkdownImpl({ content, citations, onCite, activeCite }: Props) {
  const linked = useMemo(() => content.replace(MARKER, `[$1](${CITE_PREFIX}$1)`), [content]);

  const components = useMemo<Components>(
    () => ({
      a({ href, children }) {
        const safe = safeHref(href);
        if (safe?.startsWith(CITE_PREFIX)) {
          const n = Number(safe.slice(CITE_PREFIX.length));
          const citation = citations.find((c) => c.n === n);
          const label = citation ? `${citation.title} › ${citation.heading}` : `${n}`;
          return (
            <button
              type="button"
              onClick={() => onCite?.(n)}
              title={label}
              aria-label={`[${n}] ${label}`}
              className={cn(
                "mx-0.5 inline-grid h-[18px] min-w-[18px] -translate-y-0.5 place-items-center rounded-md px-1 align-middle font-mono text-[10px] font-semibold no-underline transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-glow/60",
                activeCite === n
                  ? "bg-cyan-glow text-ink-950"
                  : "bg-iris-500/25 text-iris-300 hover:bg-iris-500/45 hover:text-white",
              )}
            >
              {n}
            </button>
          );
        }
        if (!safe) return <span>{children}</span>;
        return (
          <a href={safe} target="_blank" rel="noopener noreferrer nofollow">
            {children}
          </a>
        );
      },
      img() {
        return null;
      },
    }),
    [citations, onCite, activeCite],
  );

  return (
    <div className="prose-chat text-[15px] text-mist-100">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {linked}
      </ReactMarkdown>
    </div>
  );
}

export const AnswerMarkdown = memo(AnswerMarkdownImpl);
