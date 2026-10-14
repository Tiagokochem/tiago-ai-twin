"use client";

import { motion } from "motion/react";
import { ExternalLink } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Citation } from "@/lib/api";
import { Badge } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

const KIND_COLORS: Record<string, string> = {
  project: "text-cyan-glow bg-cyan-glow/10 border-cyan-glow/20",
  experience: "text-iris-300 bg-iris-500/15 border-iris-400/20",
  skills: "text-pink-300 bg-pink-400/10 border-pink-400/20",
  education: "text-amber-300 bg-amber-400/10 border-amber-400/20",
  faq: "text-emerald-300 bg-emerald-400/10 border-emerald-400/20",
  profile: "text-sky-300 bg-sky-400/10 border-sky-400/20",
};

export function SourcesList({
  citations,
  activeCite,
  empty,
}: {
  citations: Citation[];
  activeCite: number | null;
  empty: string;
}) {
  const refs = useRef<Record<number, HTMLLIElement | null>>({});
  useEffect(() => {
    if (activeCite) refs.current[activeCite]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeCite]);

  if (!citations.length) return <p className="px-1 text-sm text-mist-400">{empty}</p>;
  return (
    <ol className="space-y-3">
      {citations.map((c) => (
        <motion.li
          key={c.n}
          ref={(el) => {
            refs.current[c.n] = el;
          }}
          layout
          aria-current={activeCite === c.n ? "true" : undefined}
          className={cn(
            "rounded-xl border p-4 transition",
            activeCite === c.n ? "border-cyan-glow/50 bg-cyan-glow/[0.06]" : "border-white/5 bg-white/[0.02]",
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-iris-500/25 font-mono text-xs text-iris-300">
                {c.n}
              </span>
              <Badge mono className={cn("uppercase", KIND_COLORS[c.kind])}>
                {c.kind}
              </Badge>
            </div>
            {c.url && (
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={c.title}
                className="text-mist-400 hover:text-white"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
          <p className="mt-2.5 text-sm font-medium text-white">{c.title}</p>
          <p className="text-xs text-mist-400">{c.heading}</p>
          <blockquote className="mt-2 line-clamp-5 border-l-2 border-iris-400/30 pl-3 text-[13px] leading-relaxed text-mist-300">
            {c.snippet}
          </blockquote>
        </motion.li>
      ))}
    </ol>
  );
}
