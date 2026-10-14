"use client";

import { AnimatePresence, motion } from "motion/react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import type { UiMessage } from "@/lib/use-interview";
import { cn } from "@/lib/cn";

type Dict = Dictionary["interview"];

export function TraceTimeline({ message, dict }: { message: UiMessage | null; dict: Dict }) {
  if (!message || message.trace.length === 0) return <p className="px-1 text-sm text-mist-400">{dict.panel.noTrace}</p>;
  const labels: Record<string, string> = {
    start: "POST /v1/chat",
    thinking: dict.status.thinking,
    searching: dict.status.searching,
    answering: dict.status.answering,
    first_token: dict.actions.firstToken,
    done: "done",
  };
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
      <UsageGrid message={message} dict={dict} />
    </div>
  );
}

function UsageGrid({ message, dict }: { message: UiMessage; dict: Dict }) {
  const usage = message.usage;
  if (!usage) return null;
  const rows: [string, string | number][] = [
    [dict.trace.total, usage.latency_ms != null ? `${usage.latency_ms} ms` : "—"],
    [dict.trace.calls, usage.llm_calls ?? "—"],
    [dict.trace.tokens, usage.tokens?.toLocaleString() ?? "—"],
    [dict.trace.cost, usage.cost_usd != null ? `$${usage.cost_usd.toFixed(5)}` : "—"],
    [dict.trace.intent, message.intent ?? "—"],
    [dict.trace.providers, usage.providers?.join(", ") || "—"],
  ];
  return (
    <>
      <dl className="mt-2 grid grid-cols-2 gap-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-mist-400">{label}</dt>
            <dd className="mt-0.5 font-mono text-sm text-white">{value}</dd>
          </div>
        ))}
      </dl>
      {usage.prompt_version && (
        <p className="mt-2 font-mono text-[11px] text-mist-400">prompts@{usage.prompt_version}</p>
      )}
      {usage.fallback && (
        <p className="mt-3 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
          {dict.trace.fallback}: OpenAI → DeepSeek
        </p>
      )}
    </>
  );
}
