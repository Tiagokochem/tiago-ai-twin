"use client";

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible name, also shown as a tooltip. */
  label: string;
  icon: ReactNode;
  /** Show the label next to the icon from this breakpoint up. */
  showLabel?: "always" | "sm" | "never";
  active?: boolean;
  size?: "sm" | "md";
}

export const IconButton = forwardRef<HTMLButtonElement, Props>(function IconButton(
  { label, icon, showLabel = "never", active, size = "md", className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg text-sm text-mist-300 transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-400/60 disabled:pointer-events-none disabled:opacity-40",
        size === "md" ? "p-2" : "p-1.5",
        showLabel !== "never" && "px-2.5",
        active && "bg-iris-500/20 text-white",
        className,
      )}
      {...rest}
    >
      {icon}
      {showLabel === "always" && <span>{label}</span>}
      {showLabel === "sm" && <span className="hidden sm:inline">{label}</span>}
    </button>
  );
});
