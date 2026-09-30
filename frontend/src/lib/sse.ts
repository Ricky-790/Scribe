// Reads a `text/event-stream` response body and invokes a callback per event.
//
// The backend frames every event as a single `data:` line holding a JSON
// envelope of the shape { event, data }, and that is what FastAPI emits for
// both the chat and report-progress streams, so one parser serves both.

const MAX_BUFFER_BYTES = 1_000_000;

export interface StreamEvent {
  event: string;
  data: unknown;
}

function decodeEvent(block: string): StreamEvent | null {
  let name = "message";
  const dataLines = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      name = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
    // Comment lines (`:`) and unknown fields are ignored.
  }
  if (!dataLines.length) return null;

  const raw = dataLines.join("\n");
  let payload = raw;
  try {
    payload = JSON.parse(raw);
  } catch {
    // Leave non-JSON payloads as text; callers decide what to do.
  }
  return { event: name, data: payload };
}

function unwrap(envelope: unknown): StreamEvent {
  // The envelope nests the real payload under `data`, which is sometimes a
  // JSON string (double-encoded by the server).
  if (!envelope || typeof envelope !== "object") {
    return { event: "message", data: envelope };
  }

  const outer = envelope as { event?: string; data?: unknown };
  const name = outer.event || "message";
  let payload = outer.data;

  if (typeof payload === "string") {
    try {
      payload = JSON.parse(payload);
    } catch {
      // Keep the raw string — e.g. a streamed text delta.
    }
  }
  return { event: name, data: payload };
}

export interface ReadStreamOptions {
  signal?: AbortSignal;
}

export async function readEventStream(
  response: Response,
  onEvent: (event: StreamEvent) => void,
  { signal }: ReadStreamOptions = {},
): Promise<void> {
  if (!response.body) throw new Error("Response has no readable body.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const onAbort = () => {
    reader.cancel().catch(() => {});
  };
  signal?.addEventListener("abort", onAbort, { once: true });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // A malicious or truncated stream could otherwise grow this forever.
      if (buffer.length > MAX_BUFFER_BYTES) {
        throw new Error("Event stream exceeded the maximum buffer size.");
      }

      let index;
      while ((index = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        const frame = decodeEvent(block);
        if (frame) onEvent(unwrap(frame));
      }
    }
  } finally {
    signal?.removeEventListener("abort", onAbort);
    reader.releaseLock?.();
  }
}
