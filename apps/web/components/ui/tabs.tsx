"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  icon?: ReactNode;
  count?: number;
}

interface Props<T extends string> {
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  children: ReactNode;
  className?: string;
}

/** WAI-ARIA tabs: arrow keys move between tabs, the panel is labelled by the active tab. */
export function Tabs<T extends string>({ items, value, onChange, label, children, className }: Props<T>) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKey = (e: KeyboardEvent) => {
    const index = items.findIndex((i) => i.id === value);
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const next =
      e.key === "Home" ? items[0] : e.key === "End" ? items[items.length - 1] : items[(index + step + items.length) % items.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  };

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div role="tablist" aria-label={label} onKeyDown={onKey} className="flex gap-1 rounded-xl bg-white/[0.03] p-1">
        {items.map((item) => {
          const selected = item.id === value;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[item.id] = el;
              }}
              id={`${base}-tab-${item.id}`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${base}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-400/60",
                selected ? "bg-white/10 text-white" : "text-mist-400 hover:text-mist-100",
              )}
            >
              {item.icon}
              {item.label}
              {!!item.count && <span className="rounded-md bg-iris-500/30 px-1.5 font-mono text-[10px]">{item.count}</span>}
            </button>
          );
        })}
      </div>
      <div
        id={`${base}-panel`}
        role="tabpanel"
        aria-labelledby={`${base}-tab-${value}`}
        tabIndex={0}
        className="scrollbar-thin mt-4 min-h-0 flex-1 overflow-y-auto pr-1 focus-visible:outline-none"
      >
        {children}
      </div>
    </div>
  );
}
