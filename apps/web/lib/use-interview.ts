"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type ApiOptions,
  type Citation,
  type DoneEvent,
  type Lang,
  streamChat,
} from "./api";

export interface TraceStep {
  name: string;
  at: number;
}

export interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  followups: string[];
  handoff: string | null;
  intent: string | null;
  trace: TraceStep[];
  usage: DoneEvent | null;
  pending: boolean;
  error?: string;
}

export type InterviewStatus = "idle" | "thinking" | "searching" | "answering";

interface Options {
  lang: Lang;
  channel?: "web" | "widget";
  api?: ApiOptions;
  storageKey?: string;
  errors: { generic: string; rateLimited: string; tooLong: string };
}

const uid = () => Math.random().toString(36).slice(2, 10);

function assistantMessage(partial: Partial<UiMessage> = {}): UiMessage {
  return {
    id: uid(),
    role: "assistant",
    content: "",
    citations: [],
    followups: [],
    handoff: null,
    intent: null,
    trace: [],
    usage: null,
    pending: false,
    ...partial,
  };
}

export function useInterview({ lang, channel = "web", api: apiOpts, storageKey, errors }: Options) {
  const key = storageKey ?? `tiago-ai:session:${lang}`;
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [greeting, setGreeting] = useState("");
  const [starters, setStarters] = useState<string[]>([]);
  const [contactLink, setContactLink] = useState("");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [status, setStatus] = useState<InterviewStatus>("idle");
  const [ended, setEnded] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const startSession = useCallback(async () => {
    const info = await api.createSession(lang, channel, apiOpts);
    localStorage.setItem(key, info.session_id);
    setSessionId(info.session_id);
    setContactLink(info.contact_link);
    setEnded(false);
    return info.session_id;
  }, [lang, channel, apiOpts, key]);

  // Load persona copy and restore a previous conversation. The session itself
  // is created lazily on the first message.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const persona = await api.persona(apiOpts);
        if (cancelled) return;
        setGreeting(persona.messages.disclaimer[lang]);
        setStarters(persona.starter_questions[lang]);
        setContactLink(persona.contact_link);
      } catch {
        if (!cancelled) setMessages([assistantMessage({ content: errors.generic, error: "init" })]);
        return;
      }
      const stored = localStorage.getItem(key);
      if (!stored) return;
      try {
        const previous = await api.getSession(stored, apiOpts);
        if (cancelled) return;
        setSessionId(stored);
        setMessages(
          previous.messages.map((m) =>
            assistantMessage({
              role: m.role,
              content: m.content,
              citations: m.citations,
              followups: m.followups,
              handoff: m.handoff_reason,
            }),
          ),
        );
      } catch {
        localStorage.removeItem(key);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, key]);

  const patchLast = useCallback((fn: (m: UiMessage) => UiMessage) => {
    setMessages((all) => {
      const copy = [...all];
      copy[copy.length - 1] = fn(copy[copy.length - 1]);
      return copy;
    });
  }, []);

  const send = useCallback(
    async (text: string): Promise<(DoneEvent & { session_id: string }) | null> => {
      const question = text.trim();
      if (!question || status !== "idle") return null;
      let sid = sessionId;
      if (!sid) {
        try {
          sid = await startSession();
        } catch (err) {
          const message = err instanceof ApiError && err.status === 429 ? errors.rateLimited : errors.generic;
          setMessages((all) => [...all, assistantMessage({ content: message, error: message })]);
          return null;
        }
      }
      const started = performance.now();
      setMessages((all) => [
        ...all,
        assistantMessage({ role: "user", content: question }),
        assistantMessage({ pending: true, trace: [{ name: "start", at: 0 }] }),
      ]);
      setStatus("thinking");
      const controller = new AbortController();
      abortRef.current = controller;
      let result: (DoneEvent & { session_id: string }) | null = null;

      try {
        for await (const event of streamChat({ session_id: sid, message: question, lang }, controller.signal, apiOpts)) {
          const at = Math.round(performance.now() - started);
          switch (event.event) {
            case "status":
              setStatus(event.data as InterviewStatus);
              patchLast((m) => ({ ...m, trace: [...m.trace, { name: event.data, at }] }));
              break;
            case "token":
              setStatus("answering");
              patchLast((m) => ({ ...m, content: m.content + event.data }));
              break;
            case "final":
              patchLast((m) => ({
                ...m,
                content: m.content.trim(),
                citations: event.data.citations,
                followups: event.data.followups,
                handoff: event.data.handoff,
                intent: event.data.intent,
              }));
              if (event.data.contact_link) setContactLink(event.data.contact_link);
              break;
            case "done":
              result = { ...event.data, session_id: sid };
              patchLast((m) => ({ ...m, usage: event.data, pending: false, trace: [...m.trace, { name: "done", at }] }));
              break;
            case "error":
              patchLast((m) => ({ ...m, content: errors.generic, error: event.data.message, pending: false }));
              break;
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          const message =
            err instanceof ApiError && err.status === 429
              ? errors.rateLimited
              : err instanceof ApiError && err.status === 422
                ? errors.tooLong
                : errors.generic;
          patchLast((m) => ({ ...m, content: m.content || message, error: message, pending: false }));
          if (err instanceof ApiError && err.status === 404) {
            localStorage.removeItem(key);
            setSessionId(null);
          }
        } else {
          patchLast((m) => ({ ...m, pending: false }));
        }
      } finally {
        abortRef.current = null;
        setStatus("idle");
      }
      return result;
    },
    [sessionId, status, lang, apiOpts, startSession, patchLast, errors, key],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    stop();
    if (sessionId && messages.length) api.endSession(sessionId, apiOpts).catch(() => undefined);
    localStorage.removeItem(key);
    setSessionId(null);
    setMessages([]);
    setEnded(false);
  }, [stop, sessionId, messages.length, apiOpts, key]);

  const end = useCallback(async () => {
    if (!sessionId) return;
    await api.endSession(sessionId, apiOpts).catch(() => undefined);
    localStorage.removeItem(key);
    setEnded(true);
  }, [sessionId, apiOpts, key]);

  return {
    sessionId,
    greeting,
    starters,
    contactLink,
    messages,
    status,
    busy: status !== "idle",
    ended,
    send,
    stop,
    reset,
    end,
  };
}
