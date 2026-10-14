"use client";

import { Briefcase, Check, CircleDashed } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { api, ApiError, type ApiOptions, type JobFitReport as Report, type Lang } from "@/lib/api";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb } from "@/components/orb";
import { Dialog } from "@/components/ui/dialog";
import { LiveRegion } from "@/components/ui/primitives";
import { JobFitReport } from "./job-fit-report";
import { cn } from "@/lib/cn";

interface Props {
  open: boolean;
  onClose: () => void;
  dict: Dictionary["interview"];
  lang: Lang;
  apiOptions?: ApiOptions;
  onDiscuss: (prompt: string) => void;
}

const MIN_DESCRIPTION = 60;

export function JobFitDialog({ open, onClose, dict, lang, apiOptions, onDiscuss }: Props) {
  const t = dict.jobFit;
  const fieldId = useId();
  const [description, setDescription] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);

  // Closing the dialog (or leaving the page) cancels a running analysis.
  useEffect(() => {
    if (!open) controller.current?.abort();
  }, [open]);
  useEffect(() => () => controller.current?.abort(), []);

  const submit = async () => {
    if (description.trim().length < MIN_DESCRIPTION) {
      setError(t.tooShort);
      return;
    }
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setError("");
    setLoading(true);
    try {
      setReport(await api.jobFit(description.trim(), lang, apiOptions, current.signal));
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(
        err instanceof ApiError && err.status === 429
          ? dict.errors.rateLimited
          : err instanceof ApiError && err.status === 422
            ? dict.errors.tooLong
            : err instanceof ApiError && err.status === 503
              ? dict.errors.unavailable
              : t.unavailable,
      );
    } finally {
      if (controller.current === current) {
        controller.current = null;
        setLoading(false);
      }
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t.title} closeLabel={t.close} hideTitle>
      {loading ? (
        <Analyzing steps={t.steps} title={t.analyzing} />
      ) : report ? (
        <JobFitReport
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
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-iris-500/20 text-iris-300" aria-hidden>
              <Briefcase className="h-5 w-5" />
            </span>
            <p className="text-xl font-semibold tracking-tight text-white">{t.title}</p>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-mist-300">{t.subtitle}</p>
          <label htmlFor={fieldId} className="sr-only">
            {t.placeholder}
          </label>
          <textarea
            id={fieldId}
            data-autofocus
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t.placeholder}
            rows={10}
            aria-invalid={!!error}
            className="scrollbar-thin mt-5 w-full resize-y rounded-2xl border border-white/10 bg-ink-950/60 p-4 text-sm text-white placeholder:text-mist-400 focus:border-iris-400/50 focus:outline-none"
          />
          {error && (
            <p role="alert" className="mt-2 text-sm text-red-300">
              {error}
            </p>
          )}
          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={!description.trim()}
              className="rounded-xl bg-white px-5 py-2.5 text-sm font-medium text-ink-950 transition hover:bg-iris-300 disabled:opacity-40"
            >
              {t.submit}
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}

function Analyzing({ steps, title }: { steps: string[]; title: string }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), 2200);
    return () => clearInterval(id);
  }, [steps.length]);
  return (
    <div className="flex flex-col items-center gap-6 py-10" aria-busy>
      <Orb state="searching" size={120} />
      <p className="text-sm text-mist-300">{title}</p>
      <LiveRegion>{steps[step]}</LiveRegion>
      <ol className="space-y-2">
        {steps.map((label, i) => (
          <li key={label} className={cn("flex items-center gap-2 text-sm", i <= step ? "text-white" : "text-mist-400")}>
            {i < step ? (
              <Check className="h-4 w-4 text-emerald-400" aria-hidden />
            ) : (
              <CircleDashed className={cn("h-4 w-4", i === step && "animate-spin text-cyan-glow")} aria-hidden />
            )}
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}
