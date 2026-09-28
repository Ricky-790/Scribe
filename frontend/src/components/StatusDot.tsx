import React from "react";

interface StatusDotProps {
  status: string | null | undefined;
  className?: string;
}

// Visual treatment for report status indicators:
//   - in-progress states (pending, planning, researching, synthesizing, null)
//     -> copper with a pulsing halo
//   - done -> sage
//   - failed -> terracotta
export const StatusDot: React.FC<StatusDotProps> = ({
  status,
  className = "",
}) => {
  const normalized = (status || "").toLowerCase();

  let dot = "bg-accent";
  let ring = "ring-accent/25";
  let pulse = true;

  if (normalized === "done" || normalized === "completed") {
    dot = "bg-secondary";
    ring = "ring-secondary/25";
    pulse = false;
  } else if (normalized === "failed") {
    dot = "bg-error";
    ring = "ring-error/25";
    pulse = false;
  }

  return (
    <span className={`relative inline-flex h-2 w-2 shrink-0 ${className}`}>
      {pulse && (
        <span
          aria-hidden
          className={`animate-halo absolute inset-0 rounded-full ring-2 ${ring}`}
        />
      )}
      <span
        className={`relative inline-flex h-2 w-2 rounded-full ${dot} ${
          pulse ? "animate-status-pulse" : ""
        }`}
      />
    </span>
  );
};
