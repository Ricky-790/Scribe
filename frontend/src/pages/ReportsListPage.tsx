import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { AppShell } from "../components/AppShell";
import { StatusDot } from "../components/StatusDot";

interface ReportSummary {
  report_id: string;
  title: string | null;
  status: string | null;
}

interface ReportsListResponse {
  reports: ReportSummary[];
  limit: number;
  offset: number;
}

const statusMeta = (status: string | null) => {
  const s = (status || "").toLowerCase();
  if (s === "done" || s === "completed")
    return { label: "Complete", chip: "bg-secondary-container text-on-secondary-container" };
  if (s === "failed") return { label: "Failed", chip: "bg-error-container text-on-error-container" };
  if (s === "synthesizing" || s === "synthesis")
    return { label: "Writing", chip: "bg-accent-container text-on-accent-container" };
  if (s === "verifying" || s === "verify")
    return { label: "Verifying", chip: "bg-accent-container text-on-accent-container" };
  if (s === "researching" || s === "research")
    return { label: "Researching", chip: "bg-accent-container text-on-accent-container" };
  if (s === "planning")
    return { label: "Planning", chip: "bg-accent-container text-on-accent-container" };
  return { label: "Queued", chip: "bg-surface-container-high text-on-surface-variant" };
};

export const ReportsListPage: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiRequest("/reports/all", { token })
      .then((data: ReportsListResponse) => {
        if (cancelled) return;
        setReports(Array.isArray(data?.reports) ? data.reports : []);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : "Failed to load your reports.";
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const onOpen = (id: string) => {
    navigate(`/report/${id}`);
  };

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-container-max px-margin-mobile py-14 md:px-margin-desktop md:py-section-gap">
        <header className="mb-12 flex flex-wrap items-end justify-between gap-6 border-b border-outline-variant pb-8">
          <div>
            <p className="mb-3 font-label-sm text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
              Library
            </p>
            <h1 className="text-display-lg-mobile text-on-surface md:text-display-lg">
              Your reports
            </h1>
            <p className="mt-4 text-body-md text-body-md text-on-surface-variant">
              Everything Scribe has written up for you.
            </p>
          </div>
          {!loading && !error && reports.length > 0 && (
            <span className="badge border-outline-variant bg-surface-container-low text-on-surface-variant tabular-nums">
              {reports.length} {reports.length === 1 ? "report" : "reports"}
            </span>
          )}
        </header>

        {loading && (
          <div
            role="status"
            aria-label="Loading your reports"
            className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
          >
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="card flex min-h-[168px] flex-col gap-4 p-6">
                <div className="skeleton h-8 w-8 rounded-md" />
                <div className="skeleton h-4 w-4/5" />
                <div className="skeleton h-3 w-1/3" />
                <div className="mt-auto flex justify-between">
                  <div className="skeleton h-5 w-20 rounded-full" />
                  <div className="skeleton h-5 w-5 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div
            role="alert"
            className="animate-fade-scale flex items-start gap-3 rounded-md border border-error/30 bg-error-container px-5 py-4 text-body-md text-on-error-container"
          >
            <span className="material-symbols-outlined mt-px shrink-0 text-[20px] text-error">
              error
            </span>
            <div>
              <p className="font-medium">{error}</p>
              <button
                onClick={() => navigate("/chat")}
                className="mt-2 font-body-sm text-body-sm text-on-error-container underline underline-offset-2 opacity-80 transition-opacity hover:opacity-100"
              >
                Back to research
              </button>
            </div>
          </div>
        )}

        {!loading && !error && reports.length === 0 && (
          <div className="animate-fade-rise flex flex-col items-center justify-center gap-5 py-24 text-center">
            <div className="relative flex h-20 w-20 items-center justify-center rounded-full border border-outline-variant bg-surface-container-low">
              <span className="material-symbols-outlined text-[34px] text-outline">
                menu_book
              </span>
            </div>
            <div>
              <h2 className="font-headline-md text-headline-md text-on-surface">
                Nothing here yet
              </h2>
              <p className="mx-auto mt-3 max-w-sm text-body-md text-body-md text-on-surface-variant">
                Ask Scribe a question and the finished report will land here.
              </p>
            </div>
            <button
              onClick={() => navigate("/chat")}
              className="btn btn-primary btn-sheen px-6 py-3"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New research
            </button>
          </div>
        )}

        {!loading && !error && reports.length > 0 && (
          <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {reports.map((r, i) => (
              <ReportTile
                key={r.report_id}
                report={r}
                index={i}
                onOpen={() => onOpen(r.report_id)}
              />
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
};

const ReportTile: React.FC<{
  report: ReportSummary;
  index: number;
  onOpen: () => void;
}> = ({ report, index, onOpen }) => {
  const meta = statusMeta(report.status);

  return (
    <li>
      <button
        onClick={onOpen}
        className="card-interactive group flex h-full min-h-[172px] w-full flex-col gap-4 p-6 text-left"
      >
        <div className="flex items-start gap-3.5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary-container text-accent transition-transform duration-300 ease-out group-hover:scale-105">
            <span className="material-symbols-outlined text-[20px]">
              description
            </span>
          </span>
          <h3 className="flex-1 font-headline-sm text-headline-sm leading-snug text-on-surface transition-colors duration-200 group-hover:text-accent">
            {report.title || "Untitled report"}
          </h3>
        </div>

        <div className="mt-auto flex items-center justify-between gap-2">
          <span
            className={`badge ${meta.chip} transition-transform duration-200 group-hover:scale-[1.03]`}
          >
            <StatusDot status={report.status} />
            {meta.label}
          </span>
          <span className="material-symbols-outlined text-[20px] text-outline transition-[transform,color] duration-300 group-hover:translate-x-1 group-hover:text-accent">
            arrow_forward
          </span>
        </div>
      </button>
    </li>
  );
};
