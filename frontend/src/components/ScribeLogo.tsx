import React from "react";

interface ScribeLogoProps {
  className?: string;
  /** Hide the wordmark and render just the nib glyph. */
  glyphOnly?: boolean;
  alt?: string;
}

// Nib glyph + trailing "written lines" mark. Strokes inherit `currentColor`
// so the logo recolors with whatever text colour its container sets.
const NIB = (
  <>
    <path
      d="M7.5 4.5c0 9.2 3.4 17.2 8.5 23.5 5.1-6.3 8.5-14.3 8.5-23.5H7.5Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinejoin="round"
    />
    <path
      d="M16 4.5v13.2"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
    <circle cx="16" cy="11.6" r="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
  </>
);

const LINES = (
  <g stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
    <path d="M38 9h72" />
    <path d="M38 17h52" opacity="0.62" />
    <path d="M38 25h30" opacity="0.38" />
  </g>
);

export const ScribeLogo: React.FC<ScribeLogoProps> = ({
  className = "h-7 w-auto",
  glyphOnly = false,
  alt = "Scribe",
}) => (
  <span className={`inline-flex items-center gap-2.5 ${className}`}>
    <svg
      viewBox="5.6 2.6 20.8 26.4"
      xmlns="http://www.w3.org/2000/svg"
      className="h-full w-auto shrink-0"
      role="img"
      aria-label={alt}
    >
      {NIB}
    </svg>
    {glyphOnly ? null : (
      <>
        <svg
          viewBox="0 0 116 32"
          xmlns="http://www.w3.org/2000/svg"
          className="hidden h-[38%] w-auto shrink-0 self-center sm:block"
          aria-hidden="true"
        >
          {LINES}
        </svg>
        <span
          className="font-serif text-[1.35em] font-semibold leading-none tracking-[-0.02em]"
          style={{ fontSize: "inherit" }}
        >
          Scribe
        </span>
      </>
    )}
  </span>
);
