export interface SseMessage {
  event: string;
  data: string;
}

/**
 * Parse a text/event-stream body. Handles CRLF line endings split across
 * chunks, flushes the last block when the stream ends without a blank line,
 * and always releases the reader (also when the consumer stops early).
 */
export async function* readSse(body: ReadableStream<BufferSource>): AsyncGenerator<SseMessage> {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      // A trailing "\r" may be the first half of a "\r\n" in the next chunk.
      const safeEnd = buffer.endsWith("\r") ? buffer.length - 1 : buffer.length;
      const normalized = buffer.slice(0, safeEnd).replace(/\r\n?/g, "\n");
      const blocks = normalized.split("\n\n");
      buffer = blocks.pop()! + buffer.slice(safeEnd);
      for (const block of blocks) {
        const message = parseBlock(block);
        if (message) yield message;
      }
    }
    const last = parseBlock(buffer.replace(/\r\n?/g, "\n").trim());
    if (last) yield last;
  } finally {
    await reader.cancel().catch(() => undefined);
  }
}

function parseBlock(block: string): SseMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  return data.length ? { event, data: data.join("\n") } : null;
}
