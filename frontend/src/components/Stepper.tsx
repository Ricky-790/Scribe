import React from "react";

// Maps a backend status string to one of our 5 stepper phases.
// Returns the *index* of the active step (0..4), where 4 = done.
// If unknown, returns -1 (no step shown active).
export const STEP_PHASES = [
  "planning",
  "researching",
  "verifying",
  "synthesizing",
  "done",
];

export function statusToStepIndex(
  status: string | null | undefined,
): number {
  const s = (status || "").toLowerCase();
  if (s === "pending") return -1;
  if (s === "planning") return 0;
  if (s === "researching" || s === "research") return 1;
  // Build Claims and Challenge run here — the evidence is being checked.
  if (s === "verifying" || s === "verify" || s === "challenging") return 2;
  if (s === "synthesizing" || s === "synthesis") return 3;
  if (s === "done" || s === "completed") return 4;
  if (s === "failed") return -1;
  return -1;
}

interface StepperProps {
  activeIndex: number; // 0..4
}

const LABELS = ["Planning", "Researching", "Verifying", "Writing", "Done"];

// Visual treatment:
//  - the connecting rail fills from the left up to the active step
//  - completed steps = sage circle with a check that draws itself in
//  - active step = copper ring with an expanding halo + a filled core
//  - pending steps = hollow, dimmed
export const Stepper: React.FC<StepperProps> = ({ activeIndex }) => {
  const total = LABELS.length;
  // Active rail covers up to the center of the current step circle.
  // Step centers sit at (i + 0.5) / total of the width.
  const lineWidthPercent =
    activeIndex >= 0
      ? Math.max(0, Math.min(100, ((activeIndex + 0.5) / total) * 100))
      : 0;

  return (
    <section className="mx-auto w-full max-w-2xl px-2">
      <ol className="relative flex items-start justify-between">
        {/* Base rail */}
        <li
          aria-hidden
          className="absolute left-0 right-0 top-[15px] h-px bg-outline-variant"
        />
        {/* Filled rail */}
        <li
          aria-hidden
          className="absolute left-0 top-[15px] h-px origin-left bg-gradient-to-r from-secondary/50 to-accent transition-[width] duration-1000 ease-out"
          style={{ width: `${lineWidthPercent}%` }}
        />

        {LABELS.map((label, i) => {
          const isCompleted = activeIndex > i;
          const isActive = activeIndex === i;
          return (
            <li
              key={label}
              className="relative z-10 flex flex-1 flex-col items-center gap-3"
            >
              <span className="relative flex h-[30px] w-[30px] items-center justify-center">
                {isActive && (
                  <span
                    aria-hidden
                    className="animate-halo absolute inset-0 rounded-full border border-accent"
                  />
                )}
                <span
                  className={`relative flex h-[30px] w-[30px] items-center justify-center rounded-full border transition-[background-color,border-color,box-shadow] duration-500 ease-out ${
                    isCompleted
                      ? "border-secondary bg-secondary text-on-secondary"
                      : isActive
                        ? "border-accent bg-accent-container text-on-accent-container ring-4 ring-accent/15"
                        : "border-outline-variant bg-surface text-transparent"
                  }`}
                >
                  {isCompleted ? (
                    <span className="material-symbols-outlined text-[16px]">
                      check
                    </span>
                  ) : isActive ? (
                    <span className="h-2 w-2 animate-status-pulse rounded-full bg-accent" />
                  ) : (
                    <span className="font-mono text-[10px] tabular-nums text-outline">
                      {i + 1}
                    </span>
                  )}
                </span>
              </span>

              <span
                className={`text-center font-label-sm text-label-sm uppercase tracking-[0.12em] transition-colors duration-500 ${
                  isActive
                    ? "font-semibold text-accent"
                    : isCompleted
                      ? "text-secondary"
                      : "text-outline"
                }`}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
};
