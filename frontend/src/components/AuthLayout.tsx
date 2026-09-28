import React from "react";
import { Link } from "react-router-dom";
import { ScribeLogo } from "./ScribeLogo";
import { ThemeToggle } from "./ThemeToggle";

const NOTES = [
  {
    k: "Live",
    v: "Planning, retrieval and synthesis run as separate agents, and you can watch each one start and finish.",
  },
  {
    k: "Kept",
    v: "Every finished report stays in your library, filed against the query that produced it.",
  },
];

// Split-screen shell shared by /login and /signup so the two forms stay
// visually identical apart from their fields and copy.
export const AuthLayout: React.FC<{
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}> = ({ title, subtitle, children, footer }) => (
  <div className="grid min-h-screen bg-background text-on-surface antialiased lg:grid-cols-[1.05fr_1fr]">
    {/* Brand panel */}
    <aside className="relative hidden overflow-hidden border-r border-outline-variant bg-surface-container-lowest lg:flex lg:flex-col lg:justify-between">
      <div
        aria-hidden
        className="bg-grid pointer-events-none absolute inset-0"
      />

      <Link
        to="/"
        className="relative flex items-center gap-2.5 px-10 pt-10 text-on-surface"
      >
        <ScribeLogo className="h-6 text-[1.4rem] text-accent" />
      </Link>

      <div className="relative px-10 pb-6">
        <p className="mb-5 flex items-center gap-3 font-label-sm text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
          <span className="h-px w-8 bg-accent" />
          Research, written up
        </p>
        <h2 className="max-w-[16ch] text-display-lg-mobile text-on-surface md:text-display-lg">
          Ask it anything worth digging into.
        </h2>

        <dl className="mt-12 flex flex-col">
          {NOTES.map((n) => (
            <div
              key={n.k}
              className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-5 border-t border-outline-variant py-5 last:border-b"
            >
              <dt className="font-mono text-[11px] uppercase tracking-[0.14em] text-outline">
                {n.k}
              </dt>
              <dd className="text-body-sm text-body-sm leading-relaxed text-on-surface-variant">
                {n.v}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <p className="relative px-10 pb-10 font-body-sm text-body-sm text-outline">
        © {new Date().getFullYear()} Scribe
      </p>
    </aside>

    {/* Form panel */}
    <main className="flex flex-col px-margin-mobile py-8 md:px-margin-desktop">
      <div className="flex items-center justify-between">
        <Link
          to="/"
          aria-label="Scribe home"
          className="flex items-center text-on-surface lg:invisible"
        >
          <ScribeLogo className="h-6 text-[1.4rem] text-accent" />
        </Link>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <Link
            to="/"
            className="btn btn-ghost h-9 w-9 !rounded-full !p-0 text-[20px]"
            aria-label="Back to home"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </Link>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center py-10">
        <div className="animate-fade-rise w-full max-w-[26rem]">
          <h1 className="text-display-lg-mobile text-on-surface md:text-headline-md md:font-semibold">
            {title}
          </h1>
          <p className="mt-3 text-body-md text-body-md text-on-surface-variant">
            {subtitle}
          </p>

          <div className="card mt-8 p-7 md:p-8">{children}</div>

          <div className="mt-6 text-center">{footer}</div>
        </div>
      </div>
    </main>
  </div>
);

interface FormFieldProps {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete: string;
  minLength?: number;
}

export const FormField: React.FC<FormFieldProps> = ({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  minLength,
}) => (
  <div>
    <label className="field-label" htmlFor={id}>
      {label}
    </label>
    <input
      className="field"
      id={id}
      name={id}
      type={type}
      value={value}
      placeholder={placeholder}
      autoComplete={autoComplete}
      minLength={minLength}
      onChange={(e) => onChange(e.target.value)}
      required
    />
  </div>
);

export const FormError: React.FC<{ message: string | null }> = ({ message }) =>
  message ? (
    <div
      role="alert"
      className="animate-fade-scale flex items-start gap-2.5 rounded border border-error/30 bg-error-container px-4 py-3 text-body-sm text-body-sm text-on-error-container"
    >
      <span className="material-symbols-outlined mt-px shrink-0 text-[18px] text-error">
        error
      </span>
      <span>{message}</span>
    </div>
  ) : null;
