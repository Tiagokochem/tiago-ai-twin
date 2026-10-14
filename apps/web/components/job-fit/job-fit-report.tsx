"use client";

import { motion } from "motion/react";
import { ExternalLink, MessageSquare, RotateCcw } from "lucide-react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import type { JobFitReport as Report } from "@/lib/api";
import { AnswerMarkdown } from "@/components/interview/markdown";
import { Badge } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

const STATUS_TONE = { met: "success", partial: "warning", gap: "danger" } as const;

export function ScoreRing({ score, label }: { score: number; label: string }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const color = score >= 75 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f87171";
  return (
    <div className="relative grid h-28 w-28 shrink-0 place-items-center" role="img" aria-label={`${label}: ${score}/100`}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
        <motion.circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - score / 100) }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="text-center" aria-hidden>
        <p className="text-3xl font-semibold text-white">{score}</p>
        <p className="text-[10px] uppercase tracking-wider text-mist-400">{label}</p>
      </div>
    </div>
  );
}

interface Props {
  report: Report;
  dict: Dictionary["interview"];
  activeCite: number | null;
  onCite: (n: number) => void;
  onAgain: () => void;
  onDiscuss: () => void;
}

export function JobFitReport({ report, dict, activeCite, onCite, onAgain, onDiscuss }: Props) {
  const t = dict.jobFit;
  const label = { met: t.met, partial: t.partial, gap: t.gap };
  return (
    <div>
      <div className="flex flex-col gap-5 pr-6 sm:flex-row sm:items-center">
        <ScoreRing score={report.score} label={t.score} />
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-iris-300">{t.title}</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{report.role}</h3>
          <div className="mt-2 text-sm">
            <AnswerMarkdown content={report.summary} citations={report.citations} onCite={onCite} activeCite={activeCite} />
          </div>
        </div>
      </div>

      <ul className="mt-6 space-y-2">
        {report.requirements.map((r, i) => (
          <motion.li
            key={`${i}-${r.requirement}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.06 }}
            className="rounded-xl border border-white/5 bg-white/[0.02] p-3.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-white">{r.requirement}</p>
              <Badge tone={STATUS_TONE[r.status]}>{label[r.status]}</Badge>
            </div>
            <div className="mt-1 text-[13px] text-mist-300 [&_.prose-chat]:text-[13px] [&_.prose-chat]:text-mist-300">
              <AnswerMarkdown content={r.evidence} citations={report.citations} onCite={onCite} activeCite={activeCite} />
            </div>
          </motion.li>
        ))}
      </ul>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {(
          [
            [t.strengths, report.strengths, "text-emerald-300"],
            [t.gaps, report.gaps, "text-amber-200"],
          ] as const
        ).map(([title, items, color]) => (
          <div key={title} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
            <p className={cn("text-xs font-medium uppercase tracking-wider", color)}>{title}</p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-mist-100">
              {items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {report.citations.length > 0 && (
        <div className="mt-5">
          <p className="text-xs font-medium uppercase tracking-wider text-mist-400">{t.sources}</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {report.citations.map((c) => {
              const body = (
                <>
                  <span className="font-mono text-iris-300">{c.n}</span>
                  {c.title} › {c.heading}
                  {c.url && <ExternalLink className="h-3 w-3" />}
                </>
              );
              const style = cn(
                "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition",
                activeCite === c.n ? "border-cyan-glow/50 bg-cyan-glow/10 text-white" : "border-white/10 text-mist-300",
              );
              return (
                <li key={c.n}>
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" onFocus={() => onCite(c.n)} onMouseEnter={() => onCite(c.n)} className={style}>
                      {body}
                    </a>
                  ) : (
                    <button type="button" onClick={() => onCite(c.n)} className={style}>
                      {body}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-white/5 pt-4">
        <p className="font-mono text-[11px] text-mist-400">
          {t.searches}: {report.searches.length} · {report.latency_ms} ms · {report.usage.tokens ?? 0} tokens · $
          {(report.usage.cost_usd ?? 0).toFixed(4)}
          {report.usage.fallback ? " · fallback" : ""}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onAgain}
            className="flex items-center gap-2 rounded-xl border border-white/10 px-3.5 py-2 text-sm text-mist-100 transition hover:bg-white/5"
          >
            <RotateCcw className="h-4 w-4" /> {t.again}
          </button>
          <button
            type="button"
            onClick={onDiscuss}
            className="flex items-center gap-2 rounded-xl bg-white px-3.5 py-2 text-sm font-medium text-ink-950 transition hover:bg-iris-300"
          >
            <MessageSquare className="h-4 w-4" /> {t.talk}
          </button>
        </div>
      </div>
    </div>
  );
}
