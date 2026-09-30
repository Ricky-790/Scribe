import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AppShell } from "../components/AppShell";
import { openEventStream, ApiError } from "../lib/api";
import { readEventStream } from "../lib/sse";
import { Stepper, statusToStepIndex } from "../components/Stepper";
import { StatusLog } from "../components/StatusLog";
import type { LogEntry } from "../components/StatusLog";

type StreamState =
  | { kind: "connecting" }
  | { kind: "live" }
  | { kind: "error"; message: string }
  | { kind: "failed"; message: string };

interface ProgressEvent {
  phase?: string;
  status?: string;
  report_id?: string;
  task_name?: string | null;
  task_status?: string | null;
  msg?: string | null;
}

let logIdCounter = 1;

/** Maps a pipeline phase onto the stepper's index. */
function phaseToStep(phase: string | undefined, fallback: number): number {
  switch ((phase || "").toLowerCase()) {
    case "planning":
      return 0;
    case "research":
    case "researching":
      return 1;
    case "verify":
    case "verifying":
      return 2;
    case "synthesis":
    case "synthesizing":
      return 3;
    default:
      return fallback;
  }
}

/** Human-readable line for the status log. */
function describe(event: ProgressEvent, fallback: number): string {
  const msg = event.msg?.trim();
  const phase = (event.phase || "").toLowerCase();
  const status = (event.status || "").toLowerCase();

  if (msg) return msg;
  if (event.task_name) {
    const verb =
      event.task_status === "failed"
        ? "failed"
        : event.task_status === "done"
          ? "finished"
          : "working on";
    return `${event.task_name} — ${verb}`;
  }
  if (phase === "planning") {
    return status === "finished" ? "Research plan ready." : "Planning the research…";
  }
  if (phase === "researching" || phase === "research") {
    return status === "finished" ? "Research complete." : "Researching sources…";
  }
  if (phase === "verifying" || phase === "verify") {
    return status === "finished"
      ? "Evidence checks out."
      : "Checking claims against sources…";
  }
  if (phase === "synthesis" || phase === "synthesizing") return "Writing the report…";
  return status ? `${phase || "update"} ${status}` : `Update ${fallback + 1}`;
}

/**
 * Watches a running report over SSE.
 *
 * The server sends the current status first, then one event per pipeline
 * update, and closes with a `report` (finished) or `error` (failed) event. On
 * either of those this route hands back to /report/:id, which re-fetches and
 * renders the final document.
 */
export const ReportStreamPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { token } = useAuth();

  const [state, setState] = useState<StreamState>({ kind: "connecting" });
  const [activeStep, setActiveStep] = useState<number>(-1);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  // Read inside the stream callback, which must not re-subscribe on change.
  const activeStepRef = useRef(-1);

  const appendLog = useCallback((text: string, spinning = false) => {
    setLogs((prev) => {
      logIdCounter += 1;
      return [...prev, { id: logIdCounter, text, spinning }].slice(-50);
    });
  }, []);

  useEffect(() => {
    if (!reportId || !token) return;

    const controller = new AbortController();
    abortRef.current = controller;
    let cancelled = false;

    (async () => {
      try {
        setState({ kind: "connecting" });
        setLogs([]);

        const res = await openEventStream(`/reports/${reportId}/stream`, {
          token,
          signal: controller.signal,
        });
        if (cancelled) return;

        setState({ kind: "live" });
        appendLog("Live updates connected.", true);

        await readEventStream(
          res,
          ({ event, data }) => {
            if (cancelled) return;

            if (event === "ping") return;

            if (event === "status") {
              const payload = (data || {}) as ProgressEvent;

              // The first event only carries the stored status; later ones
              // carry the pipeline phase.
              if (payload.report_id && !payload.phase) {
                const step = statusToStepIndex(payload.status);
                setActiveStep(step >= 0 ? step : 0);
                appendLog(`Status: ${payload.status || "pending"}.`);
                return;
              }

              const step = phaseToStep(payload.phase, activeStepRef.current);
              activeStepRef.current = step;
              setActiveStep(step);
              appendLog(describe(payload, step), payload.status === "running");
              return;
            }

            if (event === "report") {
              appendLog("Report ready.", false);
              // Hand back to the report route, which renders the document.
              window.location.assign(`/report/${reportId}`);
              return;
            }

            if (event === "error") {
              const message =
                (data as { message?: string } | null)?.message ||
                "Research failed.";
              setState({ kind: "failed", message });
              appendLog(message, false);
              return;
            }

            if (event === "done") {
              setState((prev) =>
                prev.kind === "failed" ? prev : { kind: "connecting" },
              );
            }
          },
          { signal: controller.signal },
        );

        if (!cancelled) {
          // Stream ended without a terminal event — surface it rather than
          // leaving the user on a spinner forever.
          setState((prev) =>
            prev.kind === "failed" || prev.kind === "live"
              ? { kind: "error", message: "Live updates ended unexpectedly." }
              : prev,
          );
        }
      } catch (err) {
        if (cancelled || (err as Error).name === "AbortError") return;
        setState({
          kind: "error",
          message:
            err instanceof ApiError ? err.message : "Lost the live connection.",
        });
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
      abortRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, token, reloadKey]);

  const retry = () => setReloadKey((k) => k + 1);

  if (state.kind === "error") {
    return (
      <AppShell>
        <div className="flex min-h-full items-center justify-center p-margin-mobile md:p-margin-desktop">
          <div className="animate-fade-rise card w-full max-w-md p-8 text-center">
            <span className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-accent-container text-accent">
              <span className="material-symbols-outlined text-[26px]">wifi_off</span>
            </span>
            <h1 className="font-headline-md text-headline-md text-on-surface">
              Live updates interrupted
            </h1>
            <p className="mt-3 text-body-md text-body-md text-on-surface-variant">
              {state.message} Your research is still running — reconnecting will
              pick up where it left off.
            </p>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              <button onClick={retry} className="btn btn-primary px-6 py-3">
                <span className="material-symbols-outlined text-[18px]">
                  refresh
                </span>
                Reconnect
              </button>
              <Link to="/reports" className="btn btn-ghost px-6 py-3">
                Go to library
              </Link>
            </div>
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
            <div className="mt-2 flex items-center gap-3 rounded-full border border-error/30 bg-error-container px-5 py-3">
              <span className="material-symbols-outlined text-[20px] text-error">
                error
              </span>
              <p className="text-body-md text-body-md text-on-error-container">
                Scribe could not complete this research.
              </p>
            </div>
            <p className="mt-5 max-w-lg text-body-md text-body-md text-on-surface-variant">
              {state.message} Try a narrower question, or come back later —
              sometimes the sources just don’t hold up.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Link to="/chat" className="btn btn-primary px-6 py-3">
                <span className="material-symbols-outlined text-[18px]">
                  add
                </span>
                Start a new research
              </Link>
              <Link to="/reports" className="btn btn-ghost px-6 py-3">
                Go to library
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto flex min-h-full w-full max-w-container-max flex-col justify-center px-margin-mobile py-14 md:px-margin-desktop md:py-section-gap">
        <header className="mx-auto mb-14 flex w-full max-w-2xl flex-col items-center text-center">
          <span className="badge mb-6 border-outline-variant bg-surface-container-low text-on-surface-variant">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-halo rounded-full bg-accent" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
            </span>
            {state.kind === "connecting" ? "Connecting…" : "Research in progress"}
          </span>

          <h1 className="text-display-lg-mobile text-on-surface md:text-display-lg">
            Working on your report.
          </h1>

          <p className="mt-7 max-w-[46ch] text-body-lg text-on-surface-variant">
            Planning the search, working the sources, then writing it up. You can
            leave this page — the report will be waiting in your library.
          </p>
        </header>

        <div className="mb-14">
          <Stepper activeIndex={activeStep} />
        </div>

        <StatusLog entries={logs} />
      </div>
    </AppShell>
  );
};
