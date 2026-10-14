"use client";

import { AnimatePresence, motion } from "motion/react";
import { MessageSquare, Mic, Square, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type ApiOptions, type Lang } from "@/lib/api";
import type { useInterview } from "@/lib/use-interview";
import { useVoice } from "@/lib/use-voice";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb, type OrbState } from "../orb";
import { AnswerMarkdown } from "./markdown";
import { cn } from "@/lib/cn";

interface Props {
  dict: Dictionary["interview"];
  lang: Lang;
  chat: ReturnType<typeof useInterview>;
  apiOptions?: ApiOptions;
  onExit: () => void;
  onCite: (messageId: string, n: number) => void;
}

export function VoiceStage({ dict, lang, chat, apiOptions, onExit, onCite }: Props) {
  const voice = useVoice();
  const [transcribing, setTranscribing] = useState(false);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [muted, setMuted] = useState(false);

  const latest = [...chat.messages].reverse().find((m) => m.role === "assistant");
  const busy = transcribing || chat.busy;

  const orbState: OrbState = voice.recording
    ? "listening"
    : voice.playing
      ? "speaking"
      : transcribing
        ? "thinking"
        : chat.status === "idle"
          ? "idle"
          : chat.status;

  const label = voice.recording
    ? dict.status.listening
    : voice.playing
      ? dict.status.speaking
      : transcribing
        ? dict.status.transcribing
        : chat.status !== "idle"
          ? dict.status[chat.status]
          : dict.voice.hint;

  const toggle = useCallback(async () => {
    setError("");
    if (voice.playing) {
      voice.stopPlayback();
      return;
    }
    if (busy) return;
    if (!voice.recording) {
      const failure = await voice.startRecording();
      if (failure) setError(failure === "denied" ? dict.voice.denied : dict.voice.unsupported);
      return;
    }

    const audio = await voice.stopRecording();
    if (!audio || audio.size < 1200) {
      setError(dict.voice.noSpeech);
      return;
    }
    setTranscribing(true);
    let text = "";
    try {
      text = (await api.transcribe(audio, lang, apiOptions)).trim();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? dict.errors.rateLimited : dict.voice.unavailable);
    } finally {
      setTranscribing(false);
    }
    if (!text) {
      setError((current) => current || dict.voice.noSpeech);
      return;
    }
    setQuestion(text);
    const done = await chat.send(text);
    if (!done?.message_id || muted) return;
    try {
      await voice.play(await api.speak(done.session_id, done.message_id, apiOptions));
    } catch {
      setError(dict.voice.unavailable);
    }
  }, [voice, busy, dict, lang, apiOptions, chat, muted]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat) return;
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, button, [contenteditable]")) return;
      e.preventDefault();
      void toggle();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 py-8 text-center">
      <button
        onClick={() => void toggle()}
        aria-label={voice.recording ? dict.voice.stop : dict.voice.start}
        className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-cyan-glow/60"
      >
        <Orb state={orbState} level={voice.level} size={220} />
      </button>

      <AnimatePresence mode="wait">
        <motion.p
          key={label}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          className="text-sm text-mist-300"
        >
          {label}
        </motion.p>
      </AnimatePresence>

      <div className="flex items-center gap-2">
        <button
          onClick={() => void toggle()}
          disabled={busy && !voice.playing}
          className={cn(
            "flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition disabled:opacity-40",
            voice.recording ? "bg-red-500 text-white hover:bg-red-400" : "bg-white text-ink-950 hover:bg-iris-300",
          )}
        >
          {voice.recording ? <Square className="h-3.5 w-3.5 fill-current" /> : <Mic className="h-4 w-4" />}
          {voice.recording ? dict.voice.stop : dict.voice.start}
        </button>
        <button
          onClick={() => {
            setMuted((m) => !m);
            voice.stopPlayback();
          }}
          title={muted ? dict.voice.unmute : dict.voice.mute}
          className="grid h-10 w-10 place-items-center rounded-full border border-white/10 text-mist-300 transition hover:bg-white/5 hover:text-white"
        >
          {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </button>
        <button
          onClick={() => {
            voice.stopPlayback();
            onExit();
          }}
          title={dict.voice.exit}
          className="grid h-10 w-10 place-items-center rounded-full border border-white/10 text-mist-300 transition hover:bg-white/5 hover:text-white"
        >
          <MessageSquare className="h-4 w-4" />
        </button>
      </div>

      {error && <p className="text-sm text-red-300">{error}</p>}

      {question && (
        <div className="w-full max-w-2xl space-y-3 text-left">
          <p className="text-sm text-mist-400">
            {dict.voice.you}: <span className="text-mist-100">“{question}”</span>
          </p>
          {latest?.content && (
            <div className="glass scrollbar-thin max-h-[32dvh] overflow-y-auto rounded-2xl px-5 py-4">
              <AnswerMarkdown
                content={latest.content}
                citations={latest.citations}
                onCite={(n) => onCite(latest.id, n)}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
