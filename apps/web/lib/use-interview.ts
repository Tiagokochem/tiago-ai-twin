"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type AgentStatus,
  type ApiOptions,
  type Citation,
  type DoneEvent,
  type Feedback,
  type Lang,
  type StoredMessage,
  streamChat,
} from "./api";

export interface TraceStep {
  name: string;
  at: number;
}

export interface UiMessage {
  id: string;
  /** Server id of a persisted assistant answer (feedback, voice). */
  messageId?: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  followups: string[];
  handoff: string | null;
  intent: string | null;
  trace: TraceStep[];
  usage: DoneEvent | null;
  feedback: Feedback | null;
  pending: boolean;
  /** The question that produced this answer, used by retry. */
  question?: string;
  error?: string;
}

export type InterviewStatus = "idle" | AgentStatus;

export interface InterviewErrors {
  generic: string;
  rateLimited: string;
  tooLong: string;
  busy: string;
  unavailable: string;
}

interface Options {
  lang: Lang;
  channel?: "web" | "widget";
  api?: ApiOptions;
  storageKey?: string;
  errors: InterviewErrors;
}

export type SendResult = DoneEvent & { session_id: string };

let counter = 0;
const uid = () => `m${Date.now().toString(36)}${(counter++).toString(36)}`;

function message(partial: Partial<UiMessage> & Pick<UiMessage, "role">): UiMessage {
  return {
    id: uid(),
    content: "",
    citations: [],
    followups: [],
    handoff: null,
    intent: null,
    trace: [],
    usage: null,
    feedback: null,
    pending: false,
    ...partial,
  };
}

function restore(stored: StoredMessage): UiMessage {
  return message({
    id: `s${stored.id}`,
    messageId: stored.role === "assistant" ? stored.id : undefined,
    role: stored.role,
    content: stored.content,
    citations: stored.citations,
    followups: stored.followups,
    handoff: stored.handoff_reason,
    intent: stored.intent,
    feedback: stored.feedback,
    usage: stored.latency_ms != null ? { latency_ms: stored.latency_ms } : null,
  });
}

function describe(err: unknown, errors: InterviewErrors): string {
  if (!(err instanceof ApiError)) return errors.generic;
  if (err.status === 429) return errors.rateLimited;
  if (err.status === 422) return errors.tooLong;
  if (err.status === 409) return errors.busy;
  if (err.status === 503) return errors.unavailable;
  return errors.generic;
}

export function useInterview({ lang, channel = "web", api: apiOpts, storageKey, errors }: Options) {
  const key = storageKey ?? `tiago-ai:session:${channel}:${lang}`;
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [greeting, setGreeting] = useState("");
  const [starters, setStarters] = useState<string[]>([]);
  const [contactLink, setContactLink] = useState("");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [status, setStatus] = useState<InterviewStatus>("idle");
  const [online, setOnline] = useState<boolean | null>(null);
  const [ended, setEnded] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  // Bumped on reset/unmount so a late stream cannot write into a new conversation.
  const generation = useRef(0);
  const sessionRef = useRef<string | null>(null);
  const tokenBuffer = useRef<{ id: string; text: string } | null>(null);
  const frame = useRef(0);
  const optsRef = useRef(apiOpts);
  const errorsRef = useRef(errors);
  const messagesRef = useRef(messages);
  useEffect(() => {
    optsRef.current = apiOpts;
    errorsRef.current = errors;
    messagesRef.current = messages;
  });

  const patch = useCallback((id: string, fn: (m: UiMessage) => UiMessage) => {
    setMessages((all) => all.map((m) => (m.id === id ? fn(m) : m)));
  }, []);

  const flushTokens = useCallback(() => {
    cancelAnimationFrame(frame.current);
    const pending = tokenBuffer.current;
    tokenBuffer.current = null;
    if (pending?.text) patch(pending.id, (m) => ({ ...m, content: m.content + pending.text }));
  }, [patch]);

  // Tokens arrive faster than the screen refreshes: batch them per frame.
  const pushToken = useCallback(
    (id: string, text: string) => {
      if (tokenBuffer.current && tokenBuffer.current.id !== id) flushTokens();
      tokenBuffer.current = { id, text: (tokenBuffer.current?.text ?? "") + text };
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(flushTokens);
    },
    [flushTokens],
  );

  const setSession = useCallback(
    (id: string | null) => {
      sessionRef.current = id;
      setSessionId(id);
      if (id) localStorage.setItem(key, id);
      else localStorage.removeItem(key);
    },
    [key],
  );

  // Persona copy and restore of a previous conversation. The session itself
  // is created lazily on the first message.
  useEffect(() => {
    const gen = generation.current;
    const opts = optsRef.current;
    (async () => {
      try {
        const persona = await api.persona(opts);
        if (gen !== generation.current) return;
        setGreeting(persona.messages.disclaimer[lang]);
        setStarters(persona.starter_questions[lang]);
        setContactLink(persona.contact_link);
        setOnline(true);
      } catch {
        if (gen === generation.current) setOnline(false);
        return;
      }
      const stored = localStorage.getItem(key);
      if (!stored) return;
      try {
        const previous = await api.getSession(stored, opts);
        // Do not clobber a conversation the user already started meanwhile.
        if (gen !== generation.current || sessionRef.current) return;
        sessionRef.current = stored;
        setSessionId(stored);
        setMessages(previous.messages.map(restore));
      } catch {
        localStorage.removeItem(key);
      }
    })();
    return () => {
      generation.current += 1;
      abortRef.current?.abort();
      cancelAnimationFrame(frame.current);
    };
  }, [lang, key]);

  const send = useCallback(
    async (text: string): Promise<SendResult | null> => {
      const question = text.trim();
      if (!question || inFlight.current) return null;
      inFlight.current = true;
      const gen = generation.current;
      const errs = errorsRef.current;
      const opts = optsRef.current;
      const userMsg = message({ role: "user", content: question });
      const answer = message({ role: "assistant", pending: true, question, trace: [{ name: "start", at: 0 }] });
      setMessages((all) => [...all, userMsg, answer]);
      setStatus("thinking");

      const started = performance.now();
      const elapsed = () => Math.round(performance.now() - started);
      const controller = new AbortController();
      abortRef.current = controller;
      let result: SendResult | null = null;
      let firstToken = true;

      try {
        let sid = sessionRef.current;
        if (!sid) {
          const info = await api.createSession(lang, channel, opts);
          if (gen !== generation.current) return null;
          sid = info.session_id;
          setSession(sid);
          setEnded(false);
          if (info.contact_link) setContactLink(info.contact_link);
        }
        for await (const event of streamChat({ session_id: sid, message: question, lang }, controller.signal, opts)) {
          if (gen !== generation.current) break;
          switch (event.event) {
            case "status": {
              const at = elapsed();
              setStatus(event.data);
              patch(answer.id, (m) => ({ ...m, trace: [...m.trace, { name: event.data, at }] }));
              break;
            }
            case "token":
              if (firstToken) {
                firstToken = false;
                const at = elapsed();
                setStatus("answering");
                patch(answer.id, (m) => ({ ...m, trace: [...m.trace, { name: "first_token", at }] }));
              }
              pushToken(answer.id, event.data);
              break;
            case "final":
              flushTokens();
              patch(answer.id, (m) => ({
                ...m,
                content: event.data.response || m.content.trim(),
                citations: event.data.citations,
                followups: event.data.followups,
                handoff: event.data.handoff,
                intent: event.data.intent,
                error: event.data.intent === "error" ? errs.generic : m.error,
              }));
              if (event.data.contact_link) setContactLink(event.data.contact_link);
              break;
            case "done": {
              flushTokens();
              const at = elapsed();
              result = { ...event.data, session_id: sid };
              patch(answer.id, (m) => ({
                ...m,
                messageId: event.data.message_id,
                usage: event.data,
                pending: false,
                trace: [...m.trace, { name: "done", at }],
              }));
              break;
            }
            case "error":
              flushTokens();
              patch(answer.id, (m) => ({ ...m, content: m.content || errs.generic, error: event.data.message }));
              break;
          }
        }
      } catch (err) {
        flushTokens();
        if ((err as Error).name === "AbortError") {
          setMessages((all) => all.filter((m) => m.id !== answer.id || m.content));
        } else {
          const description = describe(err, errs);
          patch(answer.id, (m) => ({ ...m, content: m.content || description, error: description }));
          if (err instanceof ApiError && err.status === 404) setSession(null);
          if (err instanceof ApiError && err.status === 409 && err.message.includes("ended")) setEnded(true);
        }
      } finally {
        flushTokens();
        if (gen === generation.current) {
          patch(answer.id, (m) => (m.pending ? { ...m, pending: false } : m));
          setStatus("idle");
        }
        if (abortRef.current === controller) abortRef.current = null;
        inFlight.current = false;
      }
      return result;
    },
    [lang, channel, patch, pushToken, flushTokens, setSession],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  /** Drop a failed answer (and its question) and ask again. */
  const retry = useCallback(
    (id: string) => {
      const all = messagesRef.current;
      const index = all.findIndex((m) => m.id === id);
      const failed = all[index];
      if (!failed?.question || inFlight.current) return;
      setMessages((current) => current.filter((m) => m.id !== id && m.id !== all[index - 1]?.id));
      void send(failed.question);
    },
    [send],
  );

  const rate = useCallback(
    async (id: string, value: Feedback) => {
      const target = messagesRef.current.find((m) => m.id === id);
      const sid = sessionRef.current;
      if (!target?.messageId || !sid) return;
      const previous = target.feedback;
      patch(id, (m) => ({ ...m, feedback: value }));
      try {
        await api.feedback(sid, target.messageId, value, optsRef.current);
      } catch {
        patch(id, (m) => ({ ...m, feedback: previous }));
      }
    },
    [patch],
  );

  const reset = useCallback(() => {
    generation.current += 1;
    abortRef.current?.abort();
    inFlight.current = false;
    const sid = sessionRef.current;
    if (sid && messages.length) api.endSession(sid, optsRef.current).catch(() => undefined);
    setSession(null);
    setMessages([]);
    setStatus("idle");
    setEnded(false);
  }, [messages.length, setSession]);

  const end = useCallback(async () => {
    const sid = sessionRef.current;
    if (!sid) return;
    await api.endSession(sid, optsRef.current).catch(() => undefined);
    // Keep the id in memory so the transcript can still be downloaded.
    localStorage.removeItem(key);
    setEnded(true);
  }, [key]);

  return {
    sessionId,
    greeting,
    starters,
    contactLink,
    messages,
    status,
    online,
    busy: status !== "idle",
    ended,
    send,
    stop,
    retry,
    rate,
    reset,
    end,
  };
}

export type InterviewController = ReturnType<typeof useInterview>;
