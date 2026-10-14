"use client";

import { AnimatePresence, motion } from "motion/react";
import { MessageSquare, Mic, Square, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type ApiOptions, type Lang } from "@/lib/api";
import type { InterviewController } from "@/lib/use-interview";
import { useVoice } from "@/lib/use-voice";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import { Orb, type OrbState } from "@/components/orb";
import { AnswerMarkdown } from "@/components/interview/markdown";
import { IconButton } from "@/components/ui/icon-button";
import { LiveRegion } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

interface Props {
  dict: Dictionary["interview"];
  lang: Lang;
  chat: InterviewController;
  apiOptions?: ApiOptions;
  onExit: () => void;
  onCite: (messageId: string, n: number) => void;
}

const MIN_AUDIO_BYTES = 1200;

export function VoiceStage({ dict, lang, chat, apiOptions, onExit, onCite }: Props) {
  const voice = useVoice();
  const [transcribing, setTranscribing] = useState(false);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [muted, setMuted] = useState(false);
  // Read inside async flows, where the state captured at call time may be stale.
  const mutedRef = useRef(muted);
  const alive = useRef(true);
  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

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
    if (!audio || audio.size < MIN_AUDIO_BYTES) {
      setError(dict.voice.noSpeech);
      return;
    }
    setTranscribing(true);
    let text = "";
    try {
      text = (await api.transcribe(audio, lang, apiOptions)).trim();
    } catch (err) {
      if (alive.current)
        setError(err instanceof ApiError && err.status === 429 ? dict.errors.rateLimited : dict.voice.unavailable);
    } finally {
      if (alive.current) setTranscribing(false);
    }
    if (!alive.current) return;
    if (!text) {
      setError((current) => current || dict.voice.noSpeech);
      return;
    }
    setQuestion(text);
    const done = await chat.send(text);
    if (!alive.current || !done?.message_id || mutedRef.current) return;
    try {
      const speech = await api.speak(done.session_id, done.message_id, apiOptions);
      if (alive.current && !mutedRef.current) await voice.play(speech);
    } catch {
      if (alive.current) setError(dict.voice.unavailable);
    }
  }, [voice, busy, dict, lang, apiOptions, chat]);

  // Bind the Space shortcut once and always call the latest toggle.
  const toggleRef = useRef(toggle);
  useEffect(() => {
    toggleRef.current = toggle;
  }, [toggle]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat) return;
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, button, a, [contenteditable], [role=dialog]")) return;
      e.preventDefault();
      void toggleRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 py-8 text-center">
      <LiveRegion>{label}</LiveRegion>
      <button
        type="button"
        onClick={() => void toggle()}
        aria-label={voice.recording ? dict.voice.stop : dict.voice.start}
        aria-pressed={voice.recording}
        className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-cyan-glow/60"
      >
        <Orb state={orbState} level={voice.level} size={220} />
      </button>

      <AnimatePresence mode="wait">
        <motion.p
          key={label}
          aria-hidden
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
          type="button"
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
        <IconButton
          label={muted ? dict.voice.unmute : dict.voice.mute}
          aria-pressed={muted}
          icon={muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          onClick={() => {
            setMuted((m) => !m);
            voice.stopPlayback();
          }}
          className="h-10 w-10 justify-center rounded-full border border-white/10"
        />
        <IconButton
          label={dict.voice.exit}
          icon={<MessageSquare className="h-4 w-4" />}
          onClick={() => {
            voice.stopPlayback();
            onExit();
          }}
          className="h-10 w-10 justify-center rounded-full border border-white/10"
        />
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      )}

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
