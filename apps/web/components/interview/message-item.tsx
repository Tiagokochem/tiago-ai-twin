"use client";

import { motion } from "motion/react";
import { Mail } from "lucide-react";
import { memo } from "react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import type { Feedback } from "@/lib/api";
import type { UiMessage } from "@/lib/use-interview";
import { AnswerMarkdown } from "./markdown";
import { MessageActions } from "./message-actions";
import { WhatsappIcon } from "../icons";
import { cn } from "@/lib/cn";

interface Props {
  message: UiMessage;
  dict: Dictionary["interview"];
  statusLabel?: string;
  selected: boolean;
  /** Only passed to the selected message, so the others keep their memo. */
  activeCite: number | null;
  contactLink: string;
  onCite: (id: string, n: number) => void;
  onInspect: (id: string) => void;
  onRetry: (id: string) => void;
  onRate: (id: string, value: Feedback) => void;
}

function TypingIndicator({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm text-mist-400">
      <span className="flex gap-1" aria-hidden>
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-iris-300"
            animate={{ opacity: [0.2, 1, 0.2] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </span>
      {label}
    </div>
  );
}

function MessageItemImpl({
  message,
  dict,
  statusLabel,
  selected,
  activeCite,
  contactLink,
  onCite,
  onInspect,
  onRetry,
  onRate,
}: Props) {
  if (message.role === "user") {
    return (
      <motion.li initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <p className="sr-only">{dict.you}:</p>
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-iris-600/90 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-lg shadow-iris-600/10">
          {message.content}
        </div>
      </motion.li>
    );
  }

  const isWhatsapp = contactLink.includes("wa.me");
  return (
    <motion.li initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <span
        aria-hidden
        className="mt-1 h-7 w-7 shrink-0 rounded-full bg-[conic-gradient(from_90deg,#7c5cff,#22d3ee,#f472b6,#7c5cff)] shadow-[0_0_18px_rgba(124,92,255,0.5)]"
      />
      <article
        aria-label={dict.assistant}
        aria-busy={message.pending}
        className={cn(
          "min-w-0 flex-1 rounded-2xl border px-4 py-3 transition",
          selected ? "border-iris-400/30 bg-white/[0.04]" : "border-transparent hover:bg-white/[0.02]",
          message.error && "border-red-400/20",
        )}
      >
        {message.content ? (
          <AnswerMarkdown
            content={message.content}
            citations={message.citations}
            activeCite={activeCite}
            onCite={(n) => onCite(message.id, n)}
          />
        ) : (
          <TypingIndicator label={statusLabel} />
        )}
        {message.pending && message.content && (
          <span aria-hidden className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-blink bg-iris-300" />
        )}

        {message.handoff && !message.pending && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-wa/25 bg-wa/[0.06] p-3">
            <div>
              <p className="text-sm font-medium text-white">{dict.handoff.title}</p>
              <p className="text-xs text-mist-300">{dict.handoff.body}</p>
            </div>
            <a
              href={contactLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg bg-wa px-3 py-2 text-sm font-medium text-ink-950 transition hover:brightness-110"
            >
              {isWhatsapp ? <WhatsappIcon className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
              {isWhatsapp ? dict.handoff.cta : dict.handoff.email}
            </a>
          </div>
        )}

        {!message.pending && message.content && (
          <MessageActions message={message} dict={dict} onRetry={onRetry} onRate={onRate} onInspect={onInspect} />
        )}
      </article>
    </motion.li>
  );
}

export const MessageItem = memo(MessageItemImpl);
