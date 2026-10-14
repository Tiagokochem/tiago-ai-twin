"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Orb, type OrbState } from "../orb";

interface Props {
  questions: string[];
}

const CYCLE: OrbState[] = ["idle", "thinking", "searching", "answering"];

export function HeroVisual({ questions }: Props) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setStep((s) => s + 1), 1600);
    return () => clearInterval(timer);
  }, []);

  const state = CYCLE[step % CYCLE.length];
  const question = questions[Math.floor(step / CYCLE.length) % questions.length];

  return (
    <div className="relative mx-auto grid aspect-square w-full max-w-[460px] place-items-center">
      <div className="absolute inset-0 rounded-full border border-white/5" />
      <div className="absolute inset-[12%] rounded-full border border-white/5" />
      <Orb state={state} size={300} className="max-sm:scale-75" />

      <AnimatePresence mode="wait">
        <motion.div
          key={question}
          initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -10, filter: "blur(6px)" }}
          transition={{ duration: 0.45 }}
          className="glass absolute -top-2 left-0 max-w-[85%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-mist-100 shadow-2xl"
        >
          {question}
        </motion.div>
      </AnimatePresence>

      <motion.div
        className="glass absolute -bottom-1 right-0 flex items-center gap-2 rounded-full px-3.5 py-2 font-mono text-xs text-mist-300"
        animate={{ opacity: 1 }}
      >
        <span
          className={
            state === "idle"
              ? "h-2 w-2 rounded-full bg-mist-400"
              : "h-2 w-2 animate-pulse rounded-full bg-cyan-glow"
          }
        />
        {state === "idle" ? "ready" : `${state}…`}
        {state === "answering" && <span className="text-iris-300">[1][2]</span>}
      </motion.div>
    </div>
  );
}
