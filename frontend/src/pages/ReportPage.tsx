import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { WS_BASE_URL } from "../config";
import { AppShell } from "../components/AppShell";
import { Stepper, statusToStepIndex, STEP_PHASES } from "../components/Stepper";
import { StatusLog } from "../components/StatusLog";
import type { LogEntry } from "../components/StatusLog";
import { StatusDot } from "../components/StatusDot";

interface CompletedReport {
  report_id: string;
  goal: string;
  intent: string | null;
  categories: string[] | null;
  strategy_summary: string | null;
  title: string | null;
  content: string | null;
  created_at: string;
  updated_at: string;
}

interface InProgressReport {
  report_id: string;
  status: string;
}

type ReportData =
  | { kind: "completed"; data: CompletedReport }
  | { kind: "in_progress"; data: InProgressReport }
  | { kind: "failed" }
  | { kind: "loading" }
  | { kind: "error"; message: string };

interface WsMessage {
  phase?: string;
  status?: string;
  done?: boolean;
}

let logIdCounter = 1;

// Presentation-only helpers derived from fields the API already returns.
const formatDate = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const readingTimeLabel = (content: string | null): string => {
  const words = (content || "").trim().split(/\s+/).filter(Boolean).length;
  if (!words) return "—";
  return `${Math.max(1, Math.round(words / 220))} min read`;
};

// Renders the API's snake_case intent for humans. Presentation only — the
// value itself is untouched.
const intentLabel = (intent: string | null): string =>
  (intent || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const ReportPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { token } = useAuth();

  const [state, setState] = useState<ReportData>({ kind: "loading" });
  const [activeStep, setActiveStep] = useState<number>(-1);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [wsError, setWsError] = useState<string | null>(null);
  const [originalQuery, setOriginalQuery] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);
  const doneRef = useRef(false);

  const appendLog = useCallback(
    (text: string, spinning = false) => {
      setLogs((prev) => {
        const next = [...prev, { id: logIdCounter++, text, spinning }];
        // Keep the log bounded so it doesn't grow forever.
        return next.slice(-50);
      });
    },
    [],
  );

  const refresh = useCallback(
    async (isWebSocketDriven = false) => {
      if (!reportId || !token) return;
      try {
        const data = await apiRequest(`/reports/${reportId}`, { token });
        const hasContent = data && Object.prototype.hasOwnProperty.call(data, "content");

        if (!hasContent) {
          const ip = data as InProgressReport;
          const idx = statusToStepIndex(ip.status);
          setActiveStep(idx >= 0 ? idx : 0);
          setState({ kind: "in_progress", data: ip });
          if (!isWebSocketDriven) {
            appendLog(`Current status: ${ip.status || "pending"}.`);
          }
        } else {
          const comp = data as CompletedReport;
          if (comp.content != null) {
            setOriginalQuery(comp.goal || "");
            setState({ kind: "completed", data: comp });
          } else {
            // Shape B with null content — treat as still in-progress.
            setState({ kind: "in_progress", data: { report_id: comp.report_id, status: "synthesizing" } });
            setActiveStep(statusToStepIndex("synthesizing"));
          }
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setState({ kind: "error", message: err.message });
        } else {
          setState({ kind: "error", message: "Failed to load report." });
        }
      }
    },
    [reportId, token, appendLog],
  );

  // Open WebSocket while in-progress.
  useEffect(() => {
    doneRef.current = false;
    setWsError(null);

    // Always do an initial load on mount / reportId change.
    refresh(false);

    return () => {
      doneRef.current = true;
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* noop */
        }
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, token]);

  // Connect WS when we know the report is in progress.
  useEffect(() => {
    if (state.kind !== "in_progress") return;
    if (!reportId || !token) return;
    if (wsRef.current) return; // already connected

    const url = `${WS_BASE_URL}/ws/${reportId}?token=${encodeURIComponent(token)}`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      setWsError("Failed to connect to live updates.");
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      setWsError(null);
      appendLog("Live updates connected.");
    };

    ws.onmessage = (ev) => {
      let msg: WsMessage;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      const phase = (msg.phase || "").toLowerCase();
      const status = (msg.status || "").toLowerCase();
      const done = !!msg.done;

      // Advance stepper based on phase.
      if (phase === "planning") {
        setActiveStep(0);
        appendLog(`Planning ${status || "started"}…`);
      } else if (phase === "research" || phase === "researching") {
        setActiveStep(1);
        appendLog(`Research ${status || "running"}…`);
      } else if (phase === "synthesis" || phase === "synthesizing") {
        setActiveStep(2);
        appendLog(`Synthesis ${status || "running"}…`);
      } else if (phase === "done") {
        setActiveStep(3);
        appendLog(`Done.`);
      } else if (phase === "failed") {
        appendLog(`Failed: ${status || "unknown error"}.`);
      } else if (status) {
        // Generic status update — append as log entry.
        appendLog(status);
      }

      if (done) {
        if (wsRef.current) {
          try {
            wsRef.current.close();
          } catch {
            /* noop */
          }
          wsRef.current = null;
        }
        if (phase === "failed") {
          setState({ kind: "failed" });
        } else {
          // Re-fetch to get completed content.
          refresh(true).then(() => {
            /* state updated by refresh */
          });
        }
      }
    };

    ws.onerror = () => {
      if (!doneRef.current) {
        setWsError("Live updates unavailable. Refresh to retry.");
      }
    };

    ws.onclose = () => {
      if (wsRef.current === ws) wsRef.current = null;
    };

    return () => {
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* noop */
        }
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.kind, reportId, token]);

  if (state.kind === "loading") {
    return (
      <AppShell>
        <div className="mx-auto w-full max-w-container-max px-margin-mobile py-14 md:px-margin-desktop md:py-section-gap">
          <div className="mx-auto max-w-reading-max">
            <div className="animate-fade-in flex items-center justify-center gap-3 py-8">
              <span className="material-symbols-outlined animate-spin-slow text-[20px] text-accent">
                progress_activity
              </span>
              <p className="text-body-md text-body-md text-on-surface-variant">
                Loading report…
              </p>
            </div>
            <div className="mt-10 flex flex-col gap-6" aria-hidden>
              <div className="skeleton h-4 w-32" />
              <div className="skeleton h-11 w-full" />
              <div className="skeleton h-11 w-2/3" />
              <div className="skeleton mt-4 h-16 w-full" />
              <div className="skeleton h-4 w-full" />
              <div className="skeleton h-4 w-11/12" />
              <div className="skeleton h-4 w-4/5" />
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (state.kind === "error") {
    return (
      <AppShell>
        <div className="flex min-h-full items-center justify-center p-margin-mobile md:p-margin-desktop">
          <div className="animate-fade-rise card w-full max-w-md p-8 text-center">
            <span className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-error-container text-error">
              <span className="material-symbols-outlined text-[26px]">
                error
              </span>
            </span>
            <h1 className="font-headline-md text-headline-md text-on-surface">
              Could not load report
            </h1>
            <p className="mt-3 text-body-md text-body-md text-on-surface-variant">
              {state.message}
            </p>
            <button onClick={() => refresh(false)} className="btn btn-primary mt-7 px-6 py-3">
              <span className="material-symbols-outlined text-[18px]">
                refresh
              </span>
              Retry
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  if (state.kind === "failed") {
    return (
      <AppShell>
        <div className="flex min-h-full flex-col items-center justify-center px-margin-mobile py-20 text-center md:px-margin-desktop">
          <div className="animate-fade-rise flex w-full max-w-2xl flex-col items-center">
            {originalQuery && (
              <h1 className="font-display-lg-mobile text-display-lg-mobile text-on-surface-variant opacity-70 md:text-display-lg">
                &ldquo;{originalQuery}&rdquo;
              </h1>
            )}

            <div className="mt-10 flex items-center gap-3 rounded-full border border-error/30 bg-error-container px-5 py-3">
              <span className="material-symbols-outlined text-[20px] text-error">
                error
              </span>
              <p className="text-body-md text-body-md text-on-error-container">
                Scribe could not complete this research.
              </p>
            </div>

            <p className="mt-5 max-w-lg text-body-md text-body-md text-on-surface-variant">
              Try a narrower question, or come back later — sometimes the
              sources just don’t hold up.
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="btn btn-primary px-6 py-3"
              >
                <span className="material-symbols-outlined text-[18px]">
                  refresh
                </span>
                Try again
              </button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (state.kind === "in_progress") {
    return (
      <AppShell>
        <div className="mx-auto flex min-h-full w-full max-w-container-max flex-col justify-center px-margin-mobile py-14 md:px-margin-desktop md:py-section-gap">
          {/* Live status header */}
          <header className="mx-auto mb-14 flex w-full max-w-2xl flex-col items-center text-center">
            <span className="badge mb-6 border-outline-variant bg-surface-container-low text-on-surface-variant">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-halo rounded-full bg-accent" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
              </span>
              Research in progress
            </span>

            <h1 className="text-display-lg-mobile text-on-surface md:text-display-lg">
              {originalQuery
                ? `&ldquo;${originalQuery}&rdquo;`
                : "Working on your report."}
            </h1>

            {wsError ? (
              <p className="animate-fade-in mt-7 flex flex-wrap items-center justify-center gap-2 rounded-md border border-accent/30 bg-accent-container px-4 py-2.5 text-body-sm text-body-sm text-on-accent-container">
                <span className="material-symbols-outlined text-[18px]">
                  wifi_off
                </span>
                {wsError}
                <button
                  onClick={() => refresh(false)}
                  className="font-medium underline underline-offset-2 transition-opacity hover:opacity-75"
                >
                  Refresh
                </button>
              </p>
            ) : (
              <p className="mt-7 max-w-[46ch] text-body-lg text-on-surface-variant">
                Planning the search, working the sources, then writing it up.
                You can leave this page — the report will be waiting in your
                library.
              </p>
            )}
          </header>

          <div className="mb-14">
            <Stepper activeIndex={activeStep} />
          </div>

          <StatusLog entries={logs} />
        </div>
      </AppShell>
    );
  }

  // completed
  const report = state.data;
  const createdLabel = formatDate(report.created_at);
  const readingTime = readingTimeLabel(report.content);
  return (
    <AppShell>
      {/* Reading toolbar */}
      <div
        data-print-hide
        className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-outline-variant bg-background px-margin-mobile py-3 md:px-margin-desktop"
      >
        <Link
          to="/reports"
          className="btn btn-ghost px-2.5 py-2 text-on-surface-variant hover:text-accent"
        >
          <span className="material-symbols-outlined text-[18px]">
            arrow_back
          </span>
          <span className="hidden sm:inline">Library</span>
        </Link>

        <div className="flex items-center gap-1">
          <button
            onClick={() => window.print()}
            className="btn btn-ghost px-2.5 py-2"
            title="Export PDF"
          >
            <span className="material-symbols-outlined text-[20px]">
              picture_as_pdf
            </span>
            <span className="hidden sm:inline">Export</span>
          </button>
          <button
            className="btn btn-ghost h-9 w-9 !rounded-full !p-0 text-[20px]"
            aria-label="Bookmark"
            title="Bookmark"
          >
            <span className="material-symbols-outlined text-[20px]">
              bookmark
            </span>
          </button>
          <button
            className="btn btn-ghost h-9 w-9 !rounded-full !p-0 text-[20px]"
            aria-label="Share"
            title="Share"
          >
            <span className="material-symbols-outlined text-[20px]">share</span>
          </button>
        </div>
      </div>

      <article className="print-sheet mx-auto w-full max-w-reading-max px-margin-mobile py-12 md:py-20">
        {/* Report header */}
        <header className="mb-14">
          {report.categories && report.categories.length > 0 && (
            <div className="mb-7 flex flex-wrap gap-2">
              {report.categories.map((c) => (
                <span key={c} className="chip">
                  <span className="h-1 w-1 rounded-full bg-primary" />
                  {c}
                </span>
              ))}
            </div>
          )}

          <h1 className="text-display-lg-mobile text-on-surface md:text-display-lg">
            {report.title || "Untitled report"}
          </h1>

          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-body-sm text-body-sm text-on-surface-variant">
            <span className="inline-flex items-center gap-1.5">
              <StatusDot status="done" />
              Complete
            </span>
            {createdLabel && (
              <span className="inline-flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-outline">
                  calendar_today
                </span>
                {createdLabel}
              </span>
            )}
            <span className="inline-flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-outline">
                schedule
              </span>
              {readingTime}
            </span>
            {report.intent && (
              <span className="chip !py-0.5">
                <span className="material-symbols-outlined text-[14px] text-outline">
                  flag
                </span>
                {intentLabel(report.intent)}
              </span>
            )}
          </div>

          {report.goal && (
            <div className="mt-9 flex items-start gap-3.5 rounded-md border border-outline-variant bg-surface-container-low p-5">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary-container text-accent">
                <span className="material-symbols-outlined text-[17px]">
                  search
                </span>
              </span>
              <div className="min-w-0">
                <p className="mb-1.5 font-label-sm text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                  Original query
                </p>
                <p className="text-body-md text-body-md italic text-on-surface">
                  {report.goal}
                </p>
              </div>
            </div>
          )}

          {report.strategy_summary && (
            <details className="group mt-4 rounded-md border border-outline-variant bg-surface">
              <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 font-label-sm text-label-sm text-on-surface-variant transition-colors duration-200 hover:text-on-surface">
                <span className="material-symbols-outlined text-[18px] text-tertiary">
                  account_tree
                </span>
                How Scribe approached this
                <span className="material-symbols-outlined ml-auto text-[18px] transition-transform duration-300 group-open:rotate-180">
                  expand_more
                </span>
              </summary>
              <p className="animate-fade-in border-t border-outline-variant px-5 py-4 text-body-sm text-body-sm leading-relaxed text-on-surface-variant">
                {report.strategy_summary}
              </p>
            </details>
          )}
        </header>

        {/* Report body */}
        <div className="editorial">
          {report.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.content}
            </ReactMarkdown>
          ) : (
            <p className="text-on-surface-variant opacity-70">No content available.</p>
          )}
        </div>

        {/* Footer actions */}
        <div
          data-print-hide
          className="mt-20 flex flex-wrap items-center justify-between gap-4 border-t border-outline-variant pt-8"
        >
          <button
            onClick={() => window.print()}
            className="btn btn-outline px-5 py-3"
          >
            <span className="material-symbols-outlined text-[18px]">
              picture_as_pdf
            </span>
            Export as PDF
          </button>
          <Link to="/chat" className="btn btn-primary btn-sheen px-6 py-3">
            <span className="material-symbols-outlined text-[18px]">add</span>
            Research something else
          </Link>
        </div>
      </article>
    </AppShell>
  );
};
