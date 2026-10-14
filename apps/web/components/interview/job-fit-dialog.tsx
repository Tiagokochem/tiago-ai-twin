"use client";

import { AnimatePresence, motion } from "motion/react";
import { Briefcase, Check, CircleDashed, ExternalLink, MessageSquare, RotateCcw, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError, type ApiOptions, type JobFitReport, type Lang } from "@/lib/api";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb } from "../orb";
import { AnswerMarkdown } from "./markdown";
import { cn } from "@/lib/cn";

interface Props {
  open: boolean;
  onClose: () => void;
  dict: Dictionary["interview"];
  lang: Lang;
  apiOptions?: ApiOptions;
  onDiscuss: (prompt: string) => void;
}

const STATUS_STYLE = {
  met: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30",
  partial: "bg-amber-400/15 text-amber-200 border-amber-400/30",
  gap: "bg-red-400/10 text-red-300 border-red-400/25",
} as const;

export function JobFitDialog({ open, onClose, dict, lang, apiOptions, onDiscuss }: Props) {
  const t = dict.jobFit;
  const [description, setDescription] = useState("");
  const [report, setReport] = useState<JobFitReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeCite, setActiveCite] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const submit = async () => {
    if (description.trim().length < 60) {
      setError(t.tooShort);
      return;
    }
    setError("");
    setLoading(true);
    try {
      setReport(await api.jobFit(description.trim(), lang, apiOptions));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? dict.errors.rateLimited
          : err instanceof ApiError && err.status === 422
            ? dict.errors.tooLong
            : t.unavailable,
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-3 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal
            aria-label={t.title}
            className="glass scrollbar-thin relative max-h-[92dvh] w-full max-w-3xl overflow-y-auto rounded-3xl p-6 sm:p-8"
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={onClose}
              aria-label={t.close}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-mist-300 hover:bg-white/10 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>

            {loading ? (
              <Analyzing steps={t.steps} title={t.analyzing} />
            ) : report ? (
              <Report
                report={report}
                dict={dict}
                activeCite={activeCite}
                onCite={setActiveCite}
                onAgain={() => {
                  setReport(null);
                  setActiveCite(null);
                }}
                onDiscuss={() => {
                  onDiscuss(t.discussPrompt.replace("{role}", report.role));
                  onClose();
                }}
              />
            ) : (
              <div>
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-iris-500/20 text-iris-300">
                    <Briefcase className="h-5 w-5" />
                  </span>
                  <h2 className="text-xl font-semibold tracking-tight text-white">{t.title}</h2>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-mist-300">{t.subtitle}</p>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t.placeholder}
                  rows={10}
                  className="scrollbar-thin mt-5 w-full resize-y rounded-2xl border border-white/10 bg-ink-950/60 p-4 text-sm text-white placeholder:text-mist-400 focus:border-iris-400/50 focus:outline-none"
                />
                {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={() => void submit()}
                    disabled={!description.trim()}
                    className="rounded-xl bg-white px-5 py-2.5 text-sm font-medium text-ink-950 transition hover:bg-iris-300 disabled:opacity-40"
                  >
                    {t.submit}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Analyzing({ steps, title }: { steps: string[]; title: string }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), 2200);
    return () => clearInterval(id);
  }, [steps.length]);
  return (
    <div className="flex flex-col items-center gap-6 py-10">
      <Orb state="searching" size={120} />
      <p className="text-sm text-mist-300">{title}</p>
      <ol className="space-y-2">
        {steps.map((label, i) => (
          <li key={label} className={cn("flex items-center gap-2 text-sm", i <= step ? "text-white" : "text-mist-400")}>
            {i < step ? (
              <Check className="h-4 w-4 text-emerald-400" />
            ) : (
              <CircleDashed className={cn("h-4 w-4", i === step && "animate-spin text-cyan-glow")} />
            )}
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}

function ScoreRing({ score, label }: { score: number; label: string }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const color = score >= 75 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f87171";
  return (
    <div className="relative grid h-28 w-28 shrink-0 place-items-center">
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90">
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
      <div className="text-center">
        <p className="text-3xl font-semibold text-white">{score}</p>
        <p className="text-[10px] uppercase tracking-wider text-mist-400">{label}</p>
      </div>
    </div>
  );
}

function Report({
  report,
  dict,
  activeCite,
  onCite,
  onAgain,
  onDiscuss,
}: {
  report: JobFitReport;
  dict: Dictionary["interview"];
  activeCite: number | null;
  onCite: (n: number) => void;
  onAgain: () => void;
  onDiscuss: () => void;
}) {
  const t = dict.jobFit;
  const label = { met: t.met, partial: t.partial, gap: t.gap };
  return (
    <div>
      <div className="flex flex-col gap-5 pr-6 sm:flex-row sm:items-center">
        <ScoreRing score={report.score} label={t.score} />
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-iris-300">{t.title}</p>
          <h2 className="mt-1 text-xl font-semibold text-white">{report.role}</h2>
          <div className="mt-2 text-sm">
            <AnswerMarkdown content={report.summary} citations={report.citations} onCite={onCite} activeCite={activeCite} />
          </div>
        </div>
      </div>

      <ul className="mt-6 space-y-2">
        {report.requirements.map((r, i) => (
          <motion.li
            key={r.requirement}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.06 }}
            className="rounded-xl border border-white/5 bg-white/[0.02] p-3.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-white">{r.requirement}</p>
              <span className={cn("rounded-md border px-2 py-0.5 text-[11px] font-medium", STATUS_STYLE[r.status])}>
                {label[r.status]}
              </span>
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
          <div className="mt-2 flex flex-wrap gap-2">
            {report.citations.map((c) => (
              <a
                key={c.n}
                href={c.url ?? undefined}
                target="_blank"
                rel="noreferrer"
                onMouseEnter={() => onCite(c.n)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition",
                  activeCite === c.n ? "border-cyan-glow/50 bg-cyan-glow/10 text-white" : "border-white/10 text-mist-300",
                )}
              >
                <span className="font-mono text-iris-300">{c.n}</span>
                {c.title} › {c.heading}
                {c.url && <ExternalLink className="h-3 w-3" />}
              </a>
            ))}
          </div>
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
            onClick={onAgain}
            className="flex items-center gap-2 rounded-xl border border-white/10 px-3.5 py-2 text-sm text-mist-100 transition hover:bg-white/5"
          >
            <RotateCcw className="h-4 w-4" /> {t.again}
          </button>
          <button
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
