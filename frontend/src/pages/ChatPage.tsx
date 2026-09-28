import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AppShell } from "../components/AppShell";
import { API_BASE_URL } from "../config";

interface ChatMessage {
  id: string;
  role: "User" | "Agent" | "ResearchEvent";
  content: string;
  sequenceNo: number;
  createdAt: Date;
  streaming?: boolean;
  reportId?: string;
}
interface ResearchEvent {
  reportId: string;
  title: string;
}
interface SseEnvelope {
  event: string;
  data: string;
}

const QUICK_SUGGESTIONS = [
  "Emerging Tech Trends",
  "Supply Chain Vulnerabilities",
  "BTC vs SOL vs ETH deep research",
];

export const ChatPage: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const { conversationId: paramConversationId } = useParams<{
    conversationId: string;
  }>();

  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(
    paramConversationId ?? null,
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const abortRef = useRef<AbortController | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  // Sync param -> state when navigating between conversation URLs.
  useEffect(() => {
    setConversationId(paramConversationId ?? null);
    // Load messages when arriving on an existing conversation.
    if (!paramConversationId) {
      setMessages([]);
    } else {
      fetchConversationHistory(paramConversationId);
    }
  }, [paramConversationId]);

  // Auto-scroll to the latest message while streaming.
  useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [messages]);

  // Fetch conversation history from the backend when navigating to a conversation.
  const fetchConversationHistory = useCallback(async (conversationId: string) => {
    if (!token) return;
    try {
      const res = await fetch(
        `${API_BASE_URL}/chat/${conversationId}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!res.ok) {
        console.error("Failed to fetch conversation history");
        return;
      }
      const data = await res.json();
      // Convert the backend format to our ChatMessage format.
      const history: ChatMessage[] = (data?.messages || []).map(
        (m: any) => ({
          id: m.message_id || m.id,
          role: m.role as "User" | "Agent",
          content: m.content || m.message_content,
          sequenceNo: m.sequence_no || m.sequenceNo,
          createdAt: new Date(m.created_at || m.createdAt),
        })
      );
      setMessages(history);
    } catch (err) {
      console.error("Error fetching conversation history:", err);
    }
  }, [token]);

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      try {
        abortRef.current.abort();
      } catch {
        /* noop */
      }
      abortRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => cancelStream();
  }, [cancelStream]);

  const submit = useCallback(
    async (text: string, activeConversationId: string | null) => {
      if (!text.trim() || !token) return;

      setError(null);
      setStreaming(true);
      cancelStream();

      const controller = new AbortController();
      abortRef.current = controller;

      // Optimistic user bubble — the server will confirm via user_message_created.
      const optimisticId = `tmp-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: optimisticId, role: "User", content: text.trim(), sequenceNo: 0, createdAt: new Date() },
      ]);
      setQuery("");

      try {
        const res = await fetch(`${API_BASE_URL}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: text.trim(),
            conversation_id: activeConversationId || undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          let detail = `Request failed with status ${res.status}`;
          try {
            const data = await res.json();
            if (data?.detail) detail = data.detail;
          } catch {
            /* not json */
          }
          throw new Error(detail);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE messages are delimited by blank lines. Split out complete ones.
          let idx;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const rawEvent = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);

            // The backend uses FastAPI's EventSourceResponse which serializes
            // the event envelope into a single `data:` line. Collect any
            // `data:` lines (multi-line data is joined with newlines per spec).
            let dataStr = "";
            for (const line of rawEvent.split("\n")) {
              if (line.startsWith("data:")) {
                dataStr += (dataStr ? "\n" : "") + line.slice(5).trim();
              }
            }
            if (!dataStr) continue;

            // Try the wrapped-envelope format first:
            //   {"event": "<name>", "data": "<json-string>"}
            let envelope: SseEnvelope | null = null;
            let outer: any = null;
            try {
              outer = JSON.parse(dataStr);
            } catch {
              outer = null;
            }
            if (outer && typeof outer === "object" && outer.event) {
              envelope = outer as SseEnvelope;
            }

            const eventName = envelope?.event ?? "";
            let payload: any = null;
            if (envelope) {
              // Inner `data` is usually a JSON object (e.g. {"message_id":
              // "..."}) but may also be a JSON-encoded string in older event
              // types. Try object first, then string, otherwise leave null.
              const inner = envelope.data;
              if (inner && typeof inner === "object") {
                payload = inner;
              } else if (typeof inner === "string") {
                try {
                  payload = JSON.parse(inner);
                } catch {
                  payload = inner;
                }
              } else {
                payload = inner;
              }
            } else {
              payload = outer;
            }

            if (eventName === "conversation_created") {
              const newId = payload?.conversation_id;
              if (newId) {
                setConversationId(newId);
                // Don't navigate yet — the SSE reader is tied to this
                // component instance. React Router will unmount us mid-stream
                // if we navigate now, killing the response. We update the URL
                // *after* the `done` event in the `finally` block below.
              }
            } else if (eventName === "user_message_created") {
              // Replace the optimistic bubble with the server-confirmed one.
              setMessages((prev) => {
                const withoutOptimistic = prev.filter(
                  (m) => m.id !== optimisticId,
                );
                if (payload?.message_id || payload?.id) {
                  return [
                    ...withoutOptimistic,
                    {
                      id: payload.message_id ?? payload.id,
                      role: "User",
                      content: payload.content ?? text.trim(),
                      sequenceNo: payload.sequence_no ?? 0,
                      createdAt: payload.created_at ? new Date(payload.created_at) : new Date(),
                    },
                  ];
                }
                return withoutOptimistic;
              });
            } else if (eventName === "starting_response_stream") {
              // Ensure an assistant placeholder exists so deltas append to it.
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "Agent" && last.streaming) {
                  return prev;
                }
                return [
                  ...prev,
                  {
                    id: `stream-${Date.now()}`,
                    role: "Agent",
                    content: "",
                    streaming: true,
                    sequenceNo: 0,
                    createdAt: new Date(),
                  },
                ];
              });
            } else if (eventName === "message_delta") {
              // For deltas, payload may be a plain string (the agent's reply)
              // or an object with a `delta` field.
              const piece =
                typeof payload === "string"
                  ? payload
                  : (payload?.delta ?? payload?.response ?? "");
              if (!piece) continue;
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "Agent") {
                  next[next.length - 1] = {
                    ...last,
                    content: last.content + piece,
                    streaming: true,
                  };
                } else {
                  next.push({
                    id: `stream-${Date.now()}`,
                    role: "Agent",
                    content: piece,
                    streaming: true,
                    sequenceNo: 0,
                    createdAt: new Date(),
                  });
                }
                return next;
              });
            } else if (eventName === "message_complete") {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "Agent") {
                  next[next.length - 1] = {
                    id: payload?.message_id ?? payload?.id ?? last.id,
                    role: "Agent",
                    content: payload?.content ?? last.content,
                    streaming: false,
                    sequenceNo: payload?.sequence_no ?? last.sequenceNo ?? 0,
                    createdAt: payload?.created_at ? new Date(payload.created_at) : last.createdAt,
                  };
                } else if (payload) {
                  next.push({
                    id: payload.message_id ?? payload.id,
                    role: "Agent",
                    content: payload.content ?? "",
                    sequenceNo: payload.sequence_no ?? 0,
                    createdAt: payload.created_at ? new Date(payload.created_at) : new Date(),
                  });
                }
                return next;
              });
            } else if (eventName === "done") {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "Agent" && last.streaming) {
                  next[next.length - 1] = { ...last, streaming: false };
                }
                return next;
              });
            } else if (eventName === "Starting a research") {
              const reportData = payload as { report_id: string; title: string };
              setMessages((prev) => [
                ...prev,
                {
                  id: `research-${Date.now()}`,
                  role: "ResearchEvent",
                  content: "Starting research",
                  sequenceNo: 0,
                  createdAt: new Date(),
                  reportId: reportData?.report_id,
                },
              ]);
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          // User cancelled — quietly drop the optimistic bubble if nothing
          // was confirmed.
          setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
          return;
        }
        setError((err as Error).message || "Failed to send query.");
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      } finally {
        setStreaming(false);
        if (abortRef.current === controller) abortRef.current = null;

        // Navigate AFTER the stream ends so React Router doesn't unmount us
        // mid-stream (which would abort the fetch and drop the messages).
        // Use the live `conversationId` from state so we don't capture a stale
        // value via the closure.
        setConversationId((currentId) => {
          if (currentId && currentId !== paramConversationId) {
            // Defer the navigation so it happens after this state update
            // commits and the SSE reader has fully released the response.
            queueMicrotask(() => {
              navigate(`/chat/${currentId}`, { replace: true });
            });
          }
          return currentId;
        });
      }
    },
    [token, cancelStream, navigate, paramConversationId],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(query, conversationId);
  };

  const onSuggestion = (s: string) => {
    submit(s, conversationId);
  };

  // Empty state — show the centered "What should Scribe look into?" prompt.
  // Otherwise show the conversation scrollback + the input pinned at the bottom.
  const isEmpty = messages.length === 0;

  return (
    <AppShell>
      <div className="relative flex min-h-full flex-col">
        {/* Conversation scroll area */}
        {!isEmpty && (
          <div
            ref={scrollerRef}
            className="flex-1 overflow-y-auto px-margin-mobile py-8 md:px-margin-desktop"
          >
            <div className="mx-auto flex max-w-3xl flex-col gap-5">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} navigate={navigate} />
              ))}
              {streaming && (
                <div className="animate-fade-in flex items-center gap-2.5 self-start rounded-full border border-outline-variant bg-surface px-3.5 py-1.5">
                  <span className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="h-1.5 w-1.5 animate-status-pulse rounded-full bg-accent"
                        style={{ animationDelay: `${i * 0.18}s` }}
                      />
                    ))}
                  </span>
                  <span className="font-label-sm text-label-sm text-on-surface-variant">
                    Scribe is thinking…
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state hero */}
        {isEmpty && (
          <div className="relative flex flex-1 flex-col items-center justify-center px-margin-mobile pb-16 pt-10 md:px-margin-desktop">
            <div
              aria-hidden
              className="bg-grid pointer-events-none absolute inset-x-0 top-0 h-[420px] opacity-50"
            />
            <div className="reveal relative flex w-full max-w-2xl flex-col items-center">
              <span className="mb-8 flex h-14 w-14 items-center justify-center rounded-md border border-outline-variant bg-surface text-accent">
                <span className="material-symbols-outlined text-[26px]">
                  draw
                </span>
              </span>

              <h2 className="text-center text-display-lg-mobile text-on-surface md:text-display-lg">
                What should Scribe look into?
              </h2>
              <p
                className="mt-5 max-w-md text-center text-body-md text-body-md text-on-surface-variant"
                style={{ animationDelay: "0.08s" }}
              >
                A company, a market, a question you can’t quite settle. Scribe
                takes it from there.
              </p>

              <div
                className="mt-10 w-full"
                style={{ animationDelay: "0.14s" }}
              >
                <Composer
                  query={query}
                  onQueryChange={setQuery}
                  onSubmit={onSubmit}
                  streaming={streaming}
                  error={error}
                  size="lg"
                />
              </div>

              <div
                className="mt-6 flex flex-wrap justify-center gap-2.5"
                style={{ animationDelay: "0.22s" }}
              >
                {QUICK_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onSuggestion(s)}
                    disabled={streaming}
                    className="chip-interactive disabled:pointer-events-none disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-[15px] text-outline">
                      north_east
                    </span>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Pinned composer when there's existing conversation scrollback. */}
        {!isEmpty && (
          <div
            data-print-hide
            className="sticky bottom-0 z-20 border-t border-outline-variant bg-background px-margin-mobile py-4 md:px-margin-desktop"
          >
            <div className="mx-auto w-full max-w-3xl">
              <Composer
                query={query}
                onQueryChange={setQuery}
                onSubmit={onSubmit}
                streaming={streaming}
                error={error}
                size="sm"
              />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};

const Composer: React.FC<{
  query: string;
  onQueryChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  streaming: boolean;
  error: string | null;
  size: "sm" | "lg";
}> = ({ query, onQueryChange, onSubmit, streaming, error, size }) => {
  const canSend = !streaming && !!query.trim();
  const isLg = size === "lg";

  return (
    <form onSubmit={onSubmit} className="w-full" autoComplete="off">
      {error && (
        <div
          role="alert"
          className="animate-fade-scale mb-3 flex items-start gap-2.5 rounded-md border border-error/30 bg-error-container px-3.5 py-2.5 text-body-sm text-body-sm text-on-error-container"
        >
          <span className="material-symbols-outlined mt-px shrink-0 text-[17px] text-error">
            error
          </span>
          <span>{error}</span>
        </div>
      )}

      <div
        className={`group relative flex items-center gap-2 rounded-md border bg-surface transition-[border-color,box-shadow] duration-300 ${
          isLg ? "p-2 pl-5" : "p-1.5 pl-4"
        } border-outline-variant focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/10`}
      >
        <span className="material-symbols-outlined pointer-events-none shrink-0 text-[20px] text-outline transition-colors duration-200 group-focus-within:text-accent">
          search
        </span>

        <input
          className={`min-w-0 flex-1 bg-transparent text-on-surface outline-none placeholder:text-outline ${
            isLg
              ? "py-2.5 text-body-lg"
              : "py-2 text-body-md"
          }`}
          placeholder={
            isLg ? "Company, market, or topic…" : "Ask Scribe anything…"
          }
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          disabled={streaming}
        />

        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send"
          className={`btn shrink-0 rounded-md ${
            canSend
              ? "btn-primary btn-sheen"
              : "bg-surface-container text-outline"
          } ${isLg ? "h-11 w-11 !p-0" : "h-9 w-9 !p-0"}`}
        >
          <span className="material-symbols-outlined text-[20px]">
            {streaming ? "progress_activity" : "arrow_upward"}
          </span>
        </button>
      </div>
    </form>
  );
};

const MessageBubble: React.FC<{
  message: ChatMessage;
  navigate: (to: string) => void;
}> = ({ message, navigate }) => {
  const isUser = message.role === "User";
  const isResearchEvent = message.role === "ResearchEvent";

  if (isResearchEvent) {
    return (
      <div className="animate-fade-rise flex justify-start">
        <button
          onClick={() => message.reportId && navigate(`/report/${message.reportId}`)}
          className="group flex max-w-[85%] items-center gap-3.5 rounded-md border border-outline-variant bg-surface px-4 py-3.5 text-left transition-colors duration-200 hover:border-accent hover:bg-surface-container-lowest"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent-container text-accent">
            <span className="material-symbols-outlined animate-spin-slow text-[19px]">
              travel_explore
            </span>
          </span>
          <span className="min-w-0">
            <span className="block font-label-sm text-label-sm font-medium text-on-surface">
              Starting research
            </span>
            {message.reportId && (
              <span className="mt-0.5 block truncate font-mono text-[11px] text-on-surface-variant">
                {message.reportId}
              </span>
            )}
          </span>
          <span className="material-symbols-outlined text-[18px] text-outline transition-[transform,color] duration-300 group-hover:translate-x-0.5 group-hover:text-accent">
            arrow_forward
          </span>
        </button>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`animate-fade-rise max-w-[85%] whitespace-pre-wrap break-words rounded-md px-5 py-3 text-body-md text-body-md ${
          isUser
            ? "rounded-br-xs bg-primary-container text-on-primary-container"
            : "rounded-bl-xs border border-outline-variant bg-surface text-on-surface"
        }`}
      >
        {message.content || (
          <span className="inline-flex items-center gap-1.5 py-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 animate-status-pulse rounded-full bg-primary"
                style={{ animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </span>
        )}
        {message.streaming && message.content && (
          <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[0.15em] animate-caret bg-primary" />
        )}
      </div>
    </div>
  );
};
