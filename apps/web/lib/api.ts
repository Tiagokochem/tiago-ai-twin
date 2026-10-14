import { readSse } from "./sse";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "/api").replace(/\/$/, "");

export type Lang = "pt" | "en";

export interface Citation {
  n: number;
  document_key: string;
  title: string;
  heading: string;
  kind: string;
  url: string | null;
  snippet: string;
}

export interface SessionInfo {
  session_id: string;
  lang: Lang;
  greeting: string;
  starter_questions: string[];
  contact_link: string;
}

export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  intent: string | null;
  citations: Citation[];
  followups: string[];
  handoff_reason: string | null;
  feedback: Feedback | null;
  latency_ms: number | null;
  created_at: string;
}

export type Feedback = 1 | -1;

export interface FinalEvent {
  response: string;
  intent: string | null;
  lang: Lang;
  citations: Citation[];
  followups: string[];
  handoff: string | null;
  contact_link: string;
}

export interface DoneEvent {
  message_id?: number;
  latency_ms?: number;
  prompt_version?: string | null;
  llm_calls?: number;
  tokens?: number;
  cost_usd?: number;
  providers?: string[];
  fallback?: boolean;
  limit_reached?: boolean;
}

export const AGENT_STATUSES = ["thinking", "searching", "answering"] as const;
export type AgentStatus = (typeof AGENT_STATUSES)[number];

export const isAgentStatus = (value: unknown): value is AgentStatus =>
  AGENT_STATUSES.includes(value as AgentStatus);

export type ChatEvent =
  | { event: "status"; data: AgentStatus }
  | { event: "token"; data: string }
  | { event: "final"; data: FinalEvent }
  | { event: "done"; data: DoneEvent }
  | { event: "error"; data: { message: string } };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }

  static async from(response: Response): Promise<ApiError> {
    const text = await response.text().catch(() => "");
    try {
      const detail = (JSON.parse(text) as { detail?: unknown }).detail;
      return new ApiError(response.status, typeof detail === "string" ? detail : text);
    } catch {
      return new ApiError(response.status, text || response.statusText);
    }
  }
}

export interface ApiOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

const url = (path: string, opts?: ApiOptions) => `${opts?.baseUrl ?? API_URL}${path}`;

async function request<T>(path: string, init: RequestInit = {}, opts: ApiOptions = {}): Promise<T> {
  const response = await fetch(url(path, opts), {
    ...init,
    headers: { "content-type": "application/json", ...opts.headers, ...init.headers },
  });
  if (!response.ok) throw await ApiError.from(response);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export interface PersonaInfo {
  name: string;
  short_name: string;
  role: Record<Lang, string>;
  website: string;
  github: string | null;
  contact_link: string;
  starter_questions: Record<Lang, string[]>;
  messages: Record<"disclaimer" | "direct_contact", Record<Lang, string>>;
}

export interface JobFitRequirement {
  requirement: string;
  status: "met" | "partial" | "gap";
  evidence: string;
}

export interface JobFitReport {
  role: string;
  score: number;
  summary: string;
  requirements: JobFitRequirement[];
  strengths: string[];
  gaps: string[];
  citations: Citation[];
  searches: string[];
  latency_ms: number;
  usage: DoneEvent;
}

export const api = {
  persona: (opts?: ApiOptions) => request<PersonaInfo>("/v1/persona", {}, opts),
  createSession: (lang: Lang, channel: "web" | "widget" = "web", opts?: ApiOptions) =>
    request<SessionInfo>("/v1/sessions", { method: "POST", body: JSON.stringify({ lang, channel }) }, opts),
  getSession: (id: string, opts?: ApiOptions) =>
    request<{ session_id: string; lang: Lang; messages: StoredMessage[] }>(`/v1/sessions/${id}`, {}, opts),
  endSession: (id: string, opts?: ApiOptions) => request<void>(`/v1/sessions/${id}/end`, { method: "POST" }, opts),
  transcriptUrl: (id: string, opts?: ApiOptions) => url(`/v1/sessions/${id}/transcript`, opts),
  feedback: (sessionId: string, messageId: number, value: Feedback, opts?: ApiOptions) =>
    request<void>(
      `/v1/sessions/${sessionId}/messages/${messageId}/feedback`,
      { method: "POST", body: JSON.stringify({ value }) },
      opts,
    ),
  jobFit: (description: string, lang: Lang, opts?: ApiOptions, signal?: AbortSignal) =>
    request<JobFitReport>("/v1/job-fit", { method: "POST", body: JSON.stringify({ description, lang }), signal }, opts),
  async transcribe(audio: Blob, lang: Lang, opts: ApiOptions = {}): Promise<string> {
    const form = new FormData();
    const ext = audio.type.includes("mp4") ? "mp4" : audio.type.includes("ogg") ? "ogg" : "webm";
    form.append("audio", audio, `question.${ext}`);
    form.append("lang", lang);
    const response = await fetch(url("/v1/voice/transcribe", opts), {
      method: "POST",
      body: form,
      headers: opts.headers,
    });
    if (!response.ok) throw await ApiError.from(response);
    return ((await response.json()) as { text: string }).text;
  },
  async speak(sessionId: string, messageId: number, opts: ApiOptions = {}): Promise<Blob> {
    const response = await fetch(url("/v1/voice/speak", opts), {
      method: "POST",
      headers: { "content-type": "application/json", ...opts.headers },
      body: JSON.stringify({ session_id: sessionId, message_id: messageId }),
    });
    if (!response.ok) throw await ApiError.from(response);
    return response.blob();
  },
};

/** POST /v1/chat and yield typed server-sent events. */
export async function* streamChat(
  body: { session_id: string; message: string; lang?: Lang },
  signal?: AbortSignal,
  opts: ApiOptions = {},
): AsyncGenerator<ChatEvent> {
  const response = await fetch(url("/v1/chat", opts), {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream", ...opts.headers },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) throw await ApiError.from(response);

  for await (const message of readSse(response.body)) {
    let data: unknown;
    try {
      data = JSON.parse(message.data);
    } catch {
      continue;
    }
    if (message.event === "status" && !isAgentStatus(data)) continue;
    yield { event: message.event, data } as ChatEvent;
  }
}
