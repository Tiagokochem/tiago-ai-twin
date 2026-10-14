"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { api, type ApiOptions, type Lang } from "@/lib/api";
import { useInterview } from "@/lib/use-interview";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb, type OrbState } from "@/components/orb";
import { Inspector, type InspectorTab } from "@/components/inspector/inspector";
import { JobFitDialog } from "@/components/job-fit/job-fit-dialog";
import { VoiceStage } from "@/components/voice/voice-stage";
import { Dialog } from "@/components/ui/dialog";
import { LiveRegion } from "@/components/ui/primitives";
import { Composer } from "./composer";
import { InterviewHeader } from "./interview-header";
import { MessageItem } from "./message-item";
import { MessageList } from "./message-list";
import { Suggestions } from "./suggestions";
import { cn } from "@/lib/cn";

interface Props {
  dict: Dictionary["interview"];
  lang: Lang;
  channel?: "web" | "widget";
  apiOptions?: ApiOptions;
  embedded?: boolean;
}

export const EMBED_CLOSE_MESSAGE = "tiago-ai:close";

/** Below the lg breakpoint the inspector is a bottom sheet instead of a side panel. */
const isCompact = () => typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches;

export function Interview({ dict, lang, channel = "web", apiOptions, embedded = false }: Props) {
  const chat = useInterview({ lang, channel, api: apiOptions, errors: dict.errors });
  const { send, retry, rate } = chat;

  // ?mode=voice | ?mode=jobfit, also when the query changes on the same page.
  const mode = useSearchParams().get("mode");
  const [seenMode, setSeenMode] = useState<string | null>(null);
  const [voiceMode, setVoiceMode] = useState(false);
  const [jobFitOpen, setJobFitOpen] = useState(false);
  if (mode !== seenMode) {
    setSeenMode(mode);
    setVoiceMode(mode === "voice");
    setJobFitOpen(mode === "jobfit");
  }

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<InspectorTab>("trace");
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [pin, setPin] = useState(0);

  const latest = useMemo(() => [...chat.messages].reverse().find((m) => m.role === "assistant") ?? null, [chat.messages]);
  const selected = useMemo(
    () => chat.messages.find((m) => m.id === selectedId) ?? latest,
    [chat.messages, selectedId, latest],
  );

  const ask = useCallback(
    (text: string) => {
      setSelectedId(null);
      setActiveCite(null);
      setTab("trace");
      setPin((p) => p + 1);
      void send(text);
    },
    [send],
  );

  const showCitation = useCallback((id: string, n: number) => {
    setSelectedId(id);
    setActiveCite(n);
    setTab("sources");
    setPanelOpen(isCompact());
  }, []);

  const inspect = useCallback((id: string) => {
    setSelectedId(id);
    setActiveCite(null);
    setTab("sources");
    setPanelOpen(isCompact());
  }, []);

  const orbState: OrbState = chat.status === "idle" ? "idle" : chat.status;
  const statusLabel = chat.busy
    ? dict.status[chat.status as Exclude<typeof chat.status, "idle">]
    : chat.online === false
      ? dict.status.offline
      : chat.online
        ? dict.status.online
        : dict.status.connecting;
  const followups = !chat.busy && latest?.followups.length ? latest.followups : [];
  const lastError = latest?.error && !latest.pending ? latest.error : "";
  const empty = chat.messages.length === 0;
  const lastContent = chat.messages[chat.messages.length - 1]?.content.length ?? 0;

  const panel = <Inspector message={selected} tab={tab} onTab={setTab} activeCite={activeCite} dict={dict} />;

  return (
    <div
      className={cn(
        "mx-auto grid max-w-7xl gap-6 px-3 sm:px-5 lg:grid-cols-[minmax(0,1fr)_380px]",
        embedded ? "h-dvh" : "h-[calc(100dvh-4rem)]",
      )}
    >
      <main className="flex min-h-0 flex-col">
        <InterviewHeader
          dict={dict}
          orbState={orbState}
          statusLabel={statusLabel}
          online={chat.online}
          voiceMode={voiceMode}
          transcriptUrl={chat.sessionId && !empty ? api.transcriptUrl(chat.sessionId, apiOptions) : null}
          canEnd={!empty && !chat.ended}
          onJobFit={() => setJobFitOpen(true)}
          onVoice={() => setVoiceMode((v) => !v)}
          onReset={chat.reset}
          onEnd={() => void chat.end()}
          onPanel={() => setPanelOpen(true)}
          onCloseEmbed={embedded ? () => window.parent.postMessage({ type: EMBED_CLOSE_MESSAGE }, "*") : undefined}
        />
        <LiveRegion>{chat.busy ? statusLabel : ""}</LiveRegion>
        <LiveRegion assertive>{lastError}</LiveRegion>

        <MessageList contentKey={`${chat.messages.length}:${lastContent}`} pinKey={pin} jumpLabel={dict.actions.jumpLatest}>
          {voiceMode ? (
            <VoiceStage
              dict={dict}
              lang={lang}
              chat={chat}
              apiOptions={apiOptions}
              onExit={() => setVoiceMode(false)}
              onCite={showCitation}
            />
          ) : empty ? (
            <div className="flex min-h-full flex-col items-center justify-center gap-8 py-10 text-center">
              <Orb state={orbState} size={embedded ? 110 : 160} />
              <p className="max-w-xl text-balance text-mist-300">{chat.greeting}</p>
              <div className="w-full max-w-2xl text-left">
                <Suggestions title={dict.suggested} items={chat.starters} onPick={ask} disabled={chat.busy} />
              </div>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-5 pt-2">
              <ol className="flex flex-col gap-5" aria-label={dict.title}>
                {chat.messages.map((m) => {
                  const isSelected = m.role === "assistant" && m.id === selected?.id;
                  return (
                    <MessageItem
                      key={m.id}
                      message={m}
                      dict={dict}
                      statusLabel={m.pending ? statusLabel : undefined}
                      selected={isSelected}
                      activeCite={isSelected ? activeCite : null}
                      contactLink={chat.contactLink}
                      onCite={showCitation}
                      onInspect={inspect}
                      onRetry={retry}
                      onRate={rate}
                    />
                  );
                })}
              </ol>
              {followups.length > 0 && (
                <div className="pl-10">
                  <Suggestions title={dict.followups} items={followups} onPick={ask} />
                </div>
              )}
              {chat.ended && (
                <p
                  role="status"
                  className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-3 text-center text-sm text-emerald-200"
                >
                  {dict.ended}
                </p>
              )}
            </div>
          )}
        </MessageList>

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
      </main>

      <aside className="hidden min-h-0 py-4 lg:block" aria-label={dict.panel.label}>
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

      <div className="lg:hidden">
        <Dialog
          open={panelOpen}
          onClose={() => setPanelOpen(false)}
          title={dict.panel.label}
          closeLabel={dict.panel.hide}
          variant="sheet"
          hideTitle
        >
          <div className="h-full pt-8">{panel}</div>
        </Dialog>
      </div>
    </div>
  );
}
