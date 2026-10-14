"use client";

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/cn";

export type OrbState = "idle" | "thinking" | "searching" | "answering" | "listening" | "speaking";

interface OrbProps {
  state?: OrbState;
  /** 0..1 audio level while listening or speaking. */
  level?: number;
  size?: number;
  className?: string;
}

const SPIN: Record<OrbState, number> = {
  idle: 22,
  thinking: 5,
  searching: 3,
  answering: 9,
  listening: 12,
  speaking: 7,
};

export function Orb({ state = "idle", level = 0, size = 280, className }: OrbProps) {
  const reduced = useReducedMotion();
  const busy = state === "thinking" || state === "searching";
  const audio = state === "listening" || state === "speaking";
  const scale = audio ? 1 + Math.min(level, 1) * 0.18 : 1;

  return (
    <div
      className={cn("relative grid place-items-center", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <motion.div
        className="absolute inset-[-18%] rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(124,92,255,0.55), rgba(34,211,238,0.18) 45%, transparent 70%)",
        }}
        animate={reduced ? undefined : { opacity: busy ? [0.6, 1, 0.6] : [0.5, 0.75, 0.5], scale: busy ? [1, 1.08, 1] : [1, 1.04, 1] }}
        transition={{ duration: busy ? 1.4 : 5, repeat: Infinity, ease: "easeInOut" }}
      />

      {state === "listening" &&
        !reduced &&
        [0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="absolute inset-0 rounded-full border border-cyan-glow/40"
            initial={{ scale: 0.9, opacity: 0.7 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8, ease: "easeOut" }}
          />
        ))}

      <motion.div
        className="relative h-full w-full overflow-hidden rounded-full"
        animate={{ scale }}
        transition={{ type: "spring", stiffness: 260, damping: 18, mass: 0.6 }}
      >
        <motion.div
          className="absolute inset-[-25%]"
          style={{
            background:
              "conic-gradient(from 0deg, #7c5cff, #22d3ee, #a78bfa, #f472b6, #7c5cff, #38bdf8, #7c5cff)",
            filter: "blur(28px) saturate(1.2)",
          }}
          animate={reduced ? undefined : { rotate: 360 }}
          transition={{ duration: SPIN[state], repeat: Infinity, ease: "linear" }}
        />
        <motion.div
          className="absolute inset-[-10%] mix-blend-screen"
          style={{
            background:
              "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.55), transparent 35%), radial-gradient(circle at 70% 75%, rgba(34,211,238,0.45), transparent 40%)",
            filter: "blur(12px)",
          }}
          animate={reduced ? undefined : { rotate: -360 }}
          transition={{ duration: SPIN[state] * 1.6, repeat: Infinity, ease: "linear" }}
        />
        <div className="absolute inset-0 rounded-full shadow-[inset_0_0_60px_rgba(5,6,10,0.65),inset_0_2px_1px_rgba(255,255,255,0.25)]" />
      </motion.div>
    </div>
  );
}
