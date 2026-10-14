"use client";

import { motion, useReducedMotion } from "motion/react";
import { BookOpen, GitBranch, MessageCircle, Search, ShieldCheck, UserRound } from "lucide-react";

interface Props {
  steps: Record<"guard" | "router" | "retrieve" | "grade" | "answer" | "handoff", string>;
}

export function AgentFlow({ steps }: Props) {
  const reduced = useReducedMotion();
  const main = [
    { key: "guard", icon: ShieldCheck, label: steps.guard },
    { key: "router", icon: GitBranch, label: steps.router },
    { key: "retrieve", icon: Search, label: steps.retrieve },
    { key: "grade", icon: BookOpen, label: steps.grade },
    { key: "answer", icon: MessageCircle, label: steps.answer },
  ];

  return (
    <div className="relative">
      <div className="relative grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="pointer-events-none absolute left-[10%] right-[10%] top-1/2 hidden h-px bg-gradient-to-r from-iris-500/0 via-iris-400/40 to-cyan-glow/0 sm:block" />
        {!reduced && (
          <motion.span
            className="pointer-events-none absolute top-1/2 hidden h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-cyan-glow shadow-[0_0_16px_4px_rgba(34,211,238,0.6)] sm:block"
            initial={{ left: "10%" }}
            animate={{ left: ["10%", "90%"] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {main.map(({ key, icon: Icon, label }, i) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            className="glass relative z-10 flex flex-col items-center gap-2 rounded-2xl px-3 py-5 text-center"
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-iris-500/15 text-iris-300">
              <Icon className="h-5 w-5" />
            </span>
            <span className="text-sm font-medium text-mist-100">{label}</span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-mist-400">0{i + 1}</span>
          </motion.div>
        ))}
      </div>
      <div className="mt-3 flex justify-center sm:justify-end sm:pr-[22%]">
        <div className="flex items-center gap-2 rounded-full border border-dashed border-wa/40 bg-wa/5 px-4 py-2 text-sm text-wa">
          <UserRound className="h-4 w-4" />
          {steps.handoff}
        </div>
      </div>
    </div>
  );
}
