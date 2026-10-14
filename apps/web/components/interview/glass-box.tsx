"use client";

import { AnimatePresence, motion } from "motion/react";
import { Activity, ExternalLink, FileText } from "lucide-react";
import { useEffect, useRef } from "react";
import type { UiMessage } from "@/lib/use-interview";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { cn } from "@/lib/cn";

export type PanelTab = "sources" | "trace";

interface Props {
  message: UiMessage | null;
  tab: PanelTab;
  onTab: (tab: PanelTab) => void;
  activeCite: number | null;
  dict: Dictionary["interview"];
}

const KIND_COLORS: Record<string, string> = {
  project: "text-cyan-glow bg-cyan-glow/10",
  experience: "text-iris-300 bg-iris-500/15",
  skills: "text-pink-300 bg-pink-400/10",
  education: "text-amber-300 bg-amber-400/10",
  faq: "text-emerald-300 bg-emerald-400/10",
  profile: "text-sky-300 bg-sky-400/10",
};

export function GlassBox({ message, tab, onTab, activeCite, dict }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 rounded-xl bg-white/[0.03] p-1">
        {(
          [
            ["sources", FileText, dict.panel.sources, message?.citations.length],
            ["trace", Activity, dict.panel.trace, undefined],
          ] as const
        ).map(([id, Icon, label, count]) => (
          <button
            key={id}
            onClick={() => onTab(id)}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm transition",
              tab === id ? "bg-white/10 text-white" : "text-mist-400 hover:text-mist-100",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
            {!!count && <span className="rounded-md bg-iris-500/30 px-1.5 font-mono text-[10px]">{count}</span>}
          </button>
        ))}
      </div>
      <div className="scrollbar-thin mt-4 min-h-0 flex-1 overflow-y-auto pr-1">
        {tab === "sources" ? (
          <Sources message={message} activeCite={activeCite} empty={dict.panel.noSources} />
        ) : (
          <Trace message={message} dict={dict} />
        )}
      </div>
    </div>
  );
}

function Sources({ message, activeCite, empty }: { message: UiMessage | null; activeCite: number | null; empty: string }) {
  const refs = useRef<Record<number, HTMLDivElement | null>>({});
  useEffect(() => {
    if (activeCite) refs.current[activeCite]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeCite]);

  if (!message?.citations.length) return <p className="px-1 text-sm text-mist-400">{empty}</p>;
  return (
    <div className="space-y-3">
      {message.citations.map((c) => (
        <motion.div
          key={c.n}
          ref={(el) => {
            refs.current[c.n] = el;
          }}
          layout
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
              <span className={cn("rounded px-1.5 py-0.5 font-mono text-[10px] uppercase", KIND_COLORS[c.kind] ?? "bg-white/5")}>
                {c.kind}
              </span>
            </div>
            {c.url && (
              <a href={c.url} target="_blank" rel="noreferrer" className="text-mist-400 hover:text-white">
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
          <p className="mt-2.5 text-sm font-medium text-white">{c.title}</p>
          <p className="text-xs text-mist-400">{c.heading}</p>
          <p className="mt-2 line-clamp-5 text-[13px] leading-relaxed text-mist-300">{c.snippet}</p>
        </motion.div>
      ))}
    </div>
  );
}

function Trace({ message, dict }: { message: UiMessage | null; dict: Dictionary["interview"] }) {
  if (!message || message.trace.length === 0) return <p className="px-1 text-sm text-mist-400">{dict.panel.noTrace}</p>;
  const labels: Record<string, string> = {
    start: "POST /v1/chat",
    thinking: dict.status.thinking,
    searching: dict.status.searching,
    answering: dict.status.answering,
    done: "done",
  };
  const usage = message.usage;
  return (
    <div>
      <ol className="relative ml-2 border-l border-white/10">
        <AnimatePresence initial={false}>
          {message.trace.map((step, i) => {
            const next = message.trace[i + 1];
            return (
              <motion.li
                key={`${step.name}-${i}`}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className="mb-4 ml-4"
              >
                <span
                  className={cn(
                    "absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full",
                    step.name === "done" ? "bg-emerald-400" : next ? "bg-iris-400" : "animate-pulse bg-cyan-glow",
                  )}
                />
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm text-mist-100">{labels[step.name] ?? step.name}</span>
                  <span className="font-mono text-xs text-mist-400">+{step.at} ms</span>
                </div>
                {next && step.name !== "start" && (
                  <span className="font-mono text-[11px] text-mist-400">{next.at - step.at} ms</span>
                )}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
      {usage && (
        <dl className="mt-2 grid grid-cols-2 gap-2">
          {[
            [dict.trace.total, usage.latency_ms != null ? `${usage.latency_ms} ms` : "—"],
            [dict.trace.calls, usage.llm_calls ?? "—"],
            [dict.trace.tokens, usage.tokens?.toLocaleString() ?? "—"],
            [dict.trace.cost, usage.cost_usd != null ? `$${usage.cost_usd.toFixed(5)}` : "—"],
            [dict.trace.intent, message.intent ?? "—"],
            [dict.trace.providers, usage.providers?.join(", ") || "—"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-mist-400">{label}</dt>
              <dd className="mt-0.5 font-mono text-sm text-white">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {usage?.fallback && (
        <p className="mt-3 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
          {dict.trace.fallback}: OpenAI → DeepSeek
        </p>
      )}
    </div>
  );
}
