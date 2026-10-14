"use client";

import { AnimatePresence, motion } from "motion/react";
import { Briefcase, Download, Mic, PanelRight, Power, RotateCcw, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type ApiOptions, type Lang } from "@/lib/api";
import { useInterview } from "@/lib/use-interview";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb, type OrbState } from "../orb";
import { Composer } from "./composer";
import { GlassBox, type PanelTab } from "./glass-box";
import { JobFitDialog } from "./job-fit-dialog";
import { VoiceStage } from "./voice-stage";
import { MessageItem } from "./message-item";
import { Suggestions } from "./suggestions";
import { cn } from "@/lib/cn";

interface Props {
  dict: Dictionary["interview"];
  lang: Lang;
  channel?: "web" | "widget";
  apiOptions?: ApiOptions;
}

export function Interview({ dict, lang, channel = "web", apiOptions }: Props) {
  const params = useSearchParams();
  const chat = useInterview({ lang, channel, api: apiOptions, errors: dict.errors });
  const [voiceMode, setVoiceMode] = useState(params.get("mode") === "voice");
  const [jobFitOpen, setJobFitOpen] = useState(params.get("mode") === "jobfit");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<PanelTab>("trace");
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  const assistantMessages = chat.messages.filter((m) => m.role === "assistant");
  const latest = assistantMessages[assistantMessages.length - 1] ?? null;
  const selected = useMemo(
    () => chat.messages.find((m) => m.id === selectedId) ?? latest,
    [chat.messages, selectedId, latest],
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [chat.messages]);

  const ask = (text: string) => {
    setSelectedId(null);
    setActiveCite(null);
    setTab("trace");
    stickToBottom.current = true;
    void chat.send(text);
  };

  const orbState: OrbState = chat.status === "idle" ? "idle" : chat.status;
  const statusLabel = chat.status === "idle" ? dict.status.connecting : dict.status[chat.status];
  const followups = !chat.busy && latest?.followups.length ? latest.followups : [];
  const empty = chat.messages.length === 0;

  const panel = (
    <GlassBox
      message={selected}
      tab={tab}
      onTab={setTab}
      activeCite={activeCite}
      dict={dict}
    />
  );

  return (
    <div className="mx-auto grid h-[calc(100dvh-4rem)] max-w-7xl gap-6 px-3 sm:px-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="flex min-h-0 flex-col">
        <div className="flex items-center justify-between gap-2 py-3">
          <div className="flex items-center gap-3">
            <Orb state={orbState} size={30} />
            <div>
              <p className="text-sm font-medium">{dict.assistant}</p>
              <p className="text-xs text-mist-400">{chat.busy ? statusLabel : "online"}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-mist-300">
            <button
              onClick={() => setJobFitOpen(true)}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm transition hover:bg-white/5 hover:text-white"
              title={dict.jobFit.open}
            >
              <Briefcase className="h-4 w-4" />
              <span className="hidden sm:inline">{dict.jobFit.open}</span>
            </button>
            <button
              onClick={() => setVoiceMode((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm transition hover:bg-white/5 hover:text-white",
                voiceMode && "bg-iris-500/20 text-white",
              )}
              title={voiceMode ? dict.voice.exit : dict.voice.start}
            >
              <Mic className="h-4 w-4" />
              <span className="hidden sm:inline">{voiceMode ? dict.voice.exit : dict.voice.start}</span>
            </button>
            {chat.sessionId && chat.messages.length > 0 && (
              <a
                href={api.transcriptUrl(chat.sessionId)}
                className="rounded-lg p-2 transition hover:bg-white/5 hover:text-white"
                title={dict.export}
              >
                <Download className="h-4 w-4" />
              </a>
            )}
            <button onClick={chat.reset} className="rounded-lg p-2 transition hover:bg-white/5 hover:text-white" title={dict.newChat}>
              <RotateCcw className="h-4 w-4" />
            </button>
            {chat.messages.length > 0 && !chat.ended && (
              <button onClick={chat.end} className="rounded-lg p-2 transition hover:bg-white/5 hover:text-white" title={dict.endChat}>
                <Power className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={() => setPanelOpen(true)}
              className="flex items-center gap-1.5 rounded-lg p-2 text-sm transition hover:bg-white/5 hover:text-white lg:hidden"
            >
              <PanelRight className="h-4 w-4" /> {dict.panel.show}
            </button>
          </div>
        </div>

        <div
          ref={scrollRef}
          onScroll={(e) => {
            const el = e.currentTarget;
            stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
          }}
          className="scrollbar-thin min-h-0 flex-1 overflow-y-auto pb-4"
        >
          {voiceMode ? (
            <VoiceStage
              dict={dict}
              lang={lang}
              chat={chat}
              apiOptions={apiOptions}
              onExit={() => setVoiceMode(false)}
              onCite={(id, n) => {
                setSelectedId(id);
                setActiveCite(n);
                setTab("sources");
                setPanelOpen(true);
              }}
            />
          ) : empty ? (
            <div className="flex min-h-full flex-col items-center justify-center gap-8 py-10 text-center">
              <Orb state={orbState} size={160} />
              <p className="max-w-xl text-balance text-mist-300">{chat.greeting}</p>
              <div className="w-full max-w-2xl text-left">
                <Suggestions title={dict.suggested} items={chat.starters} onPick={ask} disabled={chat.busy} />
              </div>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-5 pt-2">
              {chat.messages.map((m) => (
                <MessageItem
                  key={m.id}
                  message={m}
                  dict={dict}
                  statusLabel={statusLabel}
                  selected={m.role === "assistant" && m.id === selected?.id}
                  activeCite={activeCite}
                  contactLink={chat.contactLink}
                  onSelect={() => setSelectedId(m.id)}
                  onCite={(n) => {
                    setActiveCite(n);
                    setTab("sources");
                    setPanelOpen(true);
                  }}
                />
              ))}
              {followups.length > 0 && (
                <div className="pl-10">
                  <Suggestions title={dict.followups} items={followups} onPick={ask} />
                </div>
              )}
              {chat.ended && (
                <p className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-3 text-center text-sm text-emerald-200">
                  {dict.ended}
                </p>
              )}
            </div>
          )}
        </div>

        <div className={cn("mx-auto w-full max-w-3xl pb-4", voiceMode && "hidden")}>
          <Composer
            placeholder={dict.placeholder}
            busy={chat.busy}
            disabled={chat.ended}
            sendLabel={dict.send}
            stopLabel={dict.stop}
            onSend={ask}
            onStop={chat.stop}
          />
        </div>
      </section>

      <aside className="hidden min-h-0 py-4 lg:block">
        <div className="glass h-full rounded-2xl p-4">{panel}</div>
      </aside>

      <JobFitDialog
        open={jobFitOpen}
        onClose={() => setJobFitOpen(false)}
        dict={dict}
        lang={lang}
        apiOptions={apiOptions}
        onDiscuss={(prompt) => {
          setVoiceMode(false);
          ask(prompt);
        }}
      />

      <AnimatePresence>
        {panelOpen && (
          <motion.div
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setPanelOpen(false)}
          >
            <motion.div
              className="glass absolute inset-x-0 bottom-0 h-[75dvh] rounded-t-3xl p-4"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setPanelOpen(false)}
                className="absolute right-4 top-4 rounded-lg p-1.5 text-mist-300 hover:bg-white/10"
                aria-label={dict.panel.hide}
              >
                <X className="h-4 w-4" />
              </button>
              <div className="h-full pt-8">{panel}</div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
