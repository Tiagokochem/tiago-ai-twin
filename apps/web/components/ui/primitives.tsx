import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const BADGE_TONES = {
  neutral: "bg-white/5 text-mist-300 border-white/10",
  iris: "bg-iris-500/20 text-iris-300 border-iris-400/20",
  success: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30",
  warning: "bg-amber-400/15 text-amber-200 border-amber-400/30",
  danger: "bg-red-400/10 text-red-300 border-red-400/25",
} as const;

export function Badge({
  tone = "neutral",
  mono,
  className,
  children,
}: {
  tone?: keyof typeof BADGE_TONES;
  mono?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium",
        mono && "font-mono",
        BADGE_TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Pass the rounding in className (e.g. rounded-full); defaults to rounded-lg. */
export function Skeleton({ className }: { className?: string }) {
  const rounded = className?.includes("rounded") ? "" : "rounded-lg";
  return <div aria-hidden className={cn("animate-pulse bg-white/[0.06]", rounded, className)} />;
}

/** Screen-reader announcements (status changes, finished answers). */
export function LiveRegion({ children, assertive }: { children: ReactNode; assertive?: boolean }) {
  return (
    <div className="sr-only" role={assertive ? "alert" : "status"} aria-live={assertive ? "assertive" : "polite"} aria-atomic>
      {children}
    </div>
  );
}
