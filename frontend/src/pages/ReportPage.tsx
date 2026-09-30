import React, { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useParams, Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { AppShell } from "../components/AppShell";
import { statusToStepIndex } from "../components/Stepper";
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
  | { kind: "failed"; data: InProgressReport }
  | { kind: "loading" }
  | { kind: "error"; message: string };


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

/**
 * Fetches a report once and decides what to render.
 *
 * A finished report renders here. Anything still running (or failed) hands off
 * to the stream route, which owns live progress — that keeps the streaming
 * machinery out of the reading view entirely.
 */
export const ReportPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { token } = useAuth();

  const [state, setState] = useState<ReportData>({ kind: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  const refresh = useCallback(async () => {
    if (!reportId || !token) return;
    try {
      const data = await apiRequest(`/reports/${reportId}`, { token });

      if (data && Object.prototype.hasOwnProperty.call(data, "content")) {
        setState({ kind: "completed", data: data as CompletedReport });
        return;
      }

      const statusReport = data as InProgressReport;
      setState(
        statusReport.status === "failed"
          ? { kind: "failed", data: statusReport }
          : { kind: "in_progress", data: statusReport },
      );
    } catch (err) {
      setState({
        kind: "error",
        message:
          err instanceof ApiError ? err.message : "Failed to load report.",
      });
    }
  }, [reportId, token]);

  useEffect(() => {
    void refresh();
  }, [refresh, reloadKey]);

  // A run that is not finished is watched on the stream route instead.
  if (state.kind === "in_progress" && reportId) {
    return <Navigate to={`/report/${reportId}/stream`} replace />;
  }

  const retry = () => setReloadKey((k) => k + 1);

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
            <button onClick={retry} className="btn btn-primary mt-7 px-6 py-3">
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

  // Every remaining branch below is the completed report.
  const report = state.data as CompletedReport;
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
