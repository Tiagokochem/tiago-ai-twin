"use client";

import { Check, Copy, PanelRight, RotateCcw, ThumbsDown, ThumbsUp, Timer } from "lucide-react";
import { useState } from "react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import type { Feedback } from "@/lib/api";
import type { UiMessage } from "@/lib/use-interview";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

interface Props {
  message: UiMessage;
  dict: Dictionary["interview"];
  onRetry: (id: string) => void;
  onRate: (id: string, value: Feedback) => void;
  onInspect: (id: string) => void;
}

const stepAt = (m: UiMessage, name: string) => m.trace.find((s) => s.name === name)?.at;
const duration = (ms: number) => (ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`);

export function MessageActions({ message, dict, onRetry, onRate, onInspect }: Props) {
  const t = dict.actions;
  const [copied, setCopied] = useState(false);
  // Both measured in the browser, as the recruiter experiences them; restored
  // messages only have the server-side latency.
  const ttft = stepAt(message, "first_token");
  const latency = stepAt(message, "done") ?? message.usage?.latency_ms;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked (e.g. insecure context) */
    }
  };

  return (
    <div className="mt-2 flex flex-wrap items-center gap-0.5 text-mist-400">
      {message.error && message.question ? (
        <IconButton
          size="sm"
          showLabel="always"
          label={t.retry}
          icon={<RotateCcw className="h-3.5 w-3.5" />}
          onClick={() => onRetry(message.id)}
          className="text-xs"
        />
      ) : (
        <IconButton
          size="sm"
          label={copied ? t.copied : t.copy}
          icon={copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          onClick={() => void copy()}
        />
      )}
      {message.messageId != null && !message.error && message.intent !== "error" && (
        <>
          {([1, -1] as const).map((value) => {
            const Icon = value === 1 ? ThumbsUp : ThumbsDown;
            const active = message.feedback === value;
            return (
              <IconButton
                key={value}
                size="sm"
                label={value === 1 ? t.helpful : t.notHelpful}
                aria-pressed={active}
                icon={<Icon className={cn("h-3.5 w-3.5", active && (value === 1 ? "text-emerald-400" : "text-red-300"))} />}
                onClick={() => onRate(message.id, value)}
              />
            );
          })}
          {message.feedback != null && <span className="sr-only" role="status">{t.thanks}</span>}
        </>
      )}
      {(message.citations.length > 0 || message.trace.length > 0) && (
        <IconButton
          size="sm"
          label={t.inspect}
          icon={<PanelRight className="h-3.5 w-3.5" />}
          onClick={() => onInspect(message.id)}
        />
      )}
      {latency != null && (
        <span
          className="ml-1 inline-flex items-center gap-1 rounded-md bg-white/[0.03] px-1.5 py-0.5 font-mono text-[10px]"
          title={`${dict.trace.total}${ttft != null ? ` · ${t.firstToken} ${ttft} ms` : ""}`}
        >
          <Timer className="h-3 w-3" />
          {ttft != null && <span>{duration(ttft)} ·</span>}
          {duration(latency)}
        </span>
      )}
    </div>
  );
}
