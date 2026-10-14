"use client";

import { motion } from "motion/react";
import { CornerDownRight } from "lucide-react";

export function Suggestions({
  title,
  items,
  onPick,
  disabled,
}: {
  title: string;
  items: string[];
  onPick: (q: string) => void;
  disabled?: boolean;
}) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-mist-400">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((q, i) => (
          <motion.button
            key={q}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            disabled={disabled}
            onClick={() => onPick(q)}
            className="group flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-left text-sm text-mist-100 transition hover:border-iris-400/40 hover:bg-iris-500/10 disabled:opacity-40"
          >
            <CornerDownRight className="h-3.5 w-3.5 shrink-0 text-iris-300 transition group-hover:translate-x-0.5" />
            {q}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
