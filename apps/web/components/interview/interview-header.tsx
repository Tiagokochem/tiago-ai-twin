"use client";

import { Briefcase, Download, Mic, PanelRight, Power, RotateCcw, X } from "lucide-react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb, type OrbState } from "@/components/orb";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

interface Props {
  dict: Dictionary["interview"];
  orbState: OrbState;
  statusLabel: string;
  online: boolean | null;
  voiceMode: boolean;
  transcriptUrl: string | null;
  canEnd: boolean;
  onJobFit: () => void;
  onVoice: () => void;
  onReset: () => void;
  onEnd: () => void;
  onPanel: () => void;
  /** Present when rendered inside the widget iframe. */
  onCloseEmbed?: () => void;
}

export function InterviewHeader({
  dict,
  orbState,
  statusLabel,
  online,
  voiceMode,
  transcriptUrl,
  canEnd,
  onJobFit,
  onVoice,
  onReset,
  onEnd,
  onPanel,
  onCloseEmbed,
}: Props) {
  return (
    <header className="flex items-center justify-between gap-2 py-3">
      <div className="flex items-center gap-3">
        <Orb state={orbState} size={30} />
        <div>
          <p className="text-sm font-medium">{dict.assistant}</p>
          <p className="flex items-center gap-1.5 text-xs text-mist-400">
            <span
              aria-hidden
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                online === false ? "bg-red-400" : online ? "bg-emerald-400" : "bg-mist-400",
              )}
            />
            {statusLabel}
          </p>
        </div>
      </div>
      <nav className="flex items-center gap-1" aria-label={dict.title}>
        <IconButton label={dict.jobFit.open} showLabel="sm" icon={<Briefcase className="h-4 w-4" />} onClick={onJobFit} />
        <IconButton
          label={voiceMode ? dict.voice.exit : dict.voice.start}
          showLabel="sm"
          active={voiceMode}
          aria-pressed={voiceMode}
          icon={<Mic className="h-4 w-4" />}
          onClick={onVoice}
        />
        {transcriptUrl && (
          <a
            href={transcriptUrl}
            aria-label={dict.export}
            title={dict.export}
            className="rounded-lg p-2 text-mist-300 transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-400/60"
          >
            <Download className="h-4 w-4" />
          </a>
        )}
        <IconButton label={dict.newChat} icon={<RotateCcw className="h-4 w-4" />} onClick={onReset} />
        {canEnd && <IconButton label={dict.endChat} icon={<Power className="h-4 w-4" />} onClick={onEnd} />}
        <IconButton
          label={dict.panel.show}
          icon={<PanelRight className="h-4 w-4" />}
          onClick={onPanel}
          className="lg:hidden"
        />
        {onCloseEmbed && <IconButton label={dict.panel.hide} icon={<X className="h-4 w-4" />} onClick={onCloseEmbed} />}
      </nav>
    </header>
  );
}
