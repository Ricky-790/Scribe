import React, { useEffect, useRef } from "react";

export interface LogEntry {
  id: number;
  text: string;
  spinning?: boolean;
}

interface StatusLogProps {
  entries: LogEntry[];
}

// Quiet status log — newest entries push older ones upward and fade out toward
// the top, so the tail of the log is always the readable part.
export const StatusLog: React.FC<StatusLogProps> = ({ entries }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [entries]);

  if (entries.length === 0) {
    return (
      <section className="mx-auto w-full max-w-2xl border-t border-outline-variant pt-8">
        <p className="font-mono-ui text-mono-ui text-outline">
          <span className="animate-status-pulse">▸</span> waiting for the first
          update…
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-2xl border-t border-outline-variant pt-8">
      <div className="mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-[16px] text-outline">
          terminal
        </span>
        <span className="font-label-sm text-[11px] font-semibold uppercase tracking-[0.14em] text-outline">
          Activity
        </span>
      </div>

      <div
        ref={containerRef}
        role="log"
        aria-live="polite"
        className="scroll-fade-y flex h-[132px] flex-col justify-end gap-1.5 overflow-hidden font-mono-ui text-mono-ui text-on-surface-variant"
      >
        {entries.map((e, idx) => {
          const isLast = idx === entries.length - 1;
          return (
            <div
              key={e.id}
              className="flex animate-fade-in items-baseline gap-2"
              style={{ opacity: isLast ? 1 : 0.55 }}
            >
              <span className="select-none text-outline">▸</span>
              {e.spinning && (
                <span className="material-symbols-outlined animate-spin-slow shrink-0 text-[13px] text-accent">
                  progress_activity
                </span>
              )}
              <span className={isLast ? "text-on-surface" : undefined}>
                {e.text}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
};
