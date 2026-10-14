"use client";

import { AnimatePresence, motion } from "motion/react";
import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface Props {
  /** Changes whenever content grows (new message or streamed tokens). */
  contentKey: unknown;
  /** Forces a scroll to the bottom (e.g. when the user sends a message). */
  pinKey: unknown;
  jumpLabel: string;
  children: ReactNode;
  className?: string;
}

/** Scroll container that follows the stream unless the reader scrolled up. */
export function MessageList({ contentKey, pinKey, jumpLabel, children, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const [away, setAway] = useState(false);

  const toBottom = useCallback((smooth = false) => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    stick.current = true;
    setAway(false);
  }, []);

  useEffect(() => {
    if (stick.current) toBottom();
  }, [contentKey, toBottom]);

  useEffect(() => {
    toBottom();
  }, [pinKey, toBottom]);

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={ref}
        onScroll={(e) => {
          const el = e.currentTarget;
          const near = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
          stick.current = near;
          setAway(!near);
        }}
        className={cn("scrollbar-thin h-full overflow-y-auto pb-4", className)}
      >
        {children}
      </div>
      <AnimatePresence>
        {away && (
          <motion.button
            type="button"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={() => toBottom(true)}
            aria-label={jumpLabel}
            title={jumpLabel}
            className="glass absolute bottom-3 left-1/2 grid h-9 w-9 -translate-x-1/2 place-items-center rounded-full text-mist-100 shadow-lg hover:text-white"
          >
            <ArrowDown className="h-4 w-4" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
