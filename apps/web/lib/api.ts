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
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  followups: string[];
  handoff_reason: string | null;
  created_at: string;
}

export interface FinalEvent {
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
  llm_calls?: number;
  tokens?: number;
  cost_usd?: number;
  providers?: string[];
  fallback?: boolean;
  limit_reached?: boolean;
}

export type ChatEvent =
  | { event: "status"; data: string }
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
}

export interface ApiOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

async function request<T>(path: string, init: RequestInit = {}, opts: ApiOptions = {}): Promise<T> {
  const response = await fetch(`${opts.baseUrl ?? API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...opts.headers, ...init.headers },
  });
  if (!response.ok) throw new ApiError(response.status, await response.text());
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

export const api = {
  persona: (opts?: ApiOptions) => request<PersonaInfo>("/v1/persona", {}, opts),
  createSession: (lang: Lang, channel: "web" | "widget" = "web", opts?: ApiOptions) =>
    request<SessionInfo>("/v1/sessions", { method: "POST", body: JSON.stringify({ lang, channel }) }, opts),
  getSession: (id: string, opts?: ApiOptions) =>
    request<{ session_id: string; lang: Lang; messages: StoredMessage[] }>(`/v1/sessions/${id}`, {}, opts),
  endSession: (id: string, opts?: ApiOptions) =>
    request<void>(`/v1/sessions/${id}/end`, { method: "POST" }, opts),
  transcriptUrl: (id: string, opts?: ApiOptions) => `${opts?.baseUrl ?? API_URL}/v1/sessions/${id}/transcript`,
  jobFit: (description: string, lang: Lang, opts?: ApiOptions) =>
    request<JobFitReport>("/v1/job-fit", { method: "POST", body: JSON.stringify({ description, lang }) }, opts),
  async transcribe(audio: Blob, lang: Lang, opts: ApiOptions = {}): Promise<string> {
    const form = new FormData();
    const ext = audio.type.includes("mp4") ? "mp4" : audio.type.includes("ogg") ? "ogg" : "webm";
    form.append("audio", audio, `question.${ext}`);
    form.append("lang", lang);
    const response = await fetch(`${opts.baseUrl ?? API_URL}/v1/voice/transcribe`, {
      method: "POST",
      body: form,
      headers: opts.headers,
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return ((await response.json()) as { text: string }).text;
  },
  async speak(sessionId: string, messageId: number, opts: ApiOptions = {}): Promise<Blob> {
    const response = await fetch(`${opts.baseUrl ?? API_URL}/v1/voice/speak`, {
      method: "POST",
      headers: { "content-type": "application/json", ...opts.headers },
      body: JSON.stringify({ session_id: sessionId, message_id: messageId }),
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.blob();
  },
};

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

/** POST /v1/chat and yield parsed server-sent events. */
export async function* streamChat(
  body: { session_id: string; message: string; lang?: Lang },
  signal?: AbortSignal,
  opts: ApiOptions = {},
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${opts.baseUrl ?? API_URL}/v1/chat`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream", ...opts.headers },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) throw new ApiError(response.status, await response.text());

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseBlock(block);
      if (parsed) yield parsed;
    }
  }
}

function parseBlock(block: string): ChatEvent | null {
  let event = "";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!event || data.length === 0) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) } as ChatEvent;
  } catch {
    return null;
  }
}
