"use client";

import { ArrowUp, Square } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface Props {
  placeholder: string;
  busy: boolean;
  disabled?: boolean;
  sendLabel: string;
  stopLabel: string;
  onSend: (text: string) => void;
  onStop: () => void;
  actions?: ReactNode;
}

export function Composer({ placeholder, busy, disabled, sendLabel, stopLabel, onSend, onStop, actions }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  const submit = () => {
    if (!text.trim() || busy || disabled) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="glass rounded-2xl p-2 shadow-2xl shadow-black/40 focus-within:border-iris-400/40">
      <textarea
        ref={ref}
        rows={1}
        value={text}
        disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={placeholder}
        className="scrollbar-thin block max-h-[200px] w-full resize-none bg-transparent px-3 py-2.5 text-[15px] text-white placeholder:text-mist-400 focus:outline-none disabled:opacity-50"
      />
      <div className="flex items-center justify-between gap-2 px-1 pb-0.5">
        <div className="flex items-center gap-1">{actions}</div>
        {busy ? (
          <button
            onClick={onStop}
            aria-label={stopLabel}
            className="grid h-9 w-9 place-items-center rounded-xl bg-white/10 text-white transition hover:bg-white/20"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
          </button>
        ) : (
          <button
            onClick={submit}
            aria-label={sendLabel}
            disabled={!text.trim() || disabled}
            className={cn(
              "grid h-9 w-9 place-items-center rounded-xl transition",
              text.trim() ? "bg-white text-ink-950 hover:bg-iris-300" : "bg-white/10 text-mist-400",
            )}
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
