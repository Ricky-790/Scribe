/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,jsx,ts,tsx,html}"],
  darkMode: ["class", '[data-theme="ink"]'],
  theme: {
    extend: {
      // Default scale skips 12/15/18/22/28/35/45/55/65/85, all of which the
      // design leans on for tinted borders, rings and washes.
      opacity: {
        3: "0.03",
        8: "0.08",
        12: "0.12",
        15: "0.15",
        18: "0.18",
        22: "0.22",
        28: "0.28",
        35: "0.35",
        45: "0.45",
        55: "0.55",
        62: "0.62",
        65: "0.65",
        85: "0.85",
      },
      colors: {
        // Every colour resolves through a CSS custom property so the two themes
        // can be swapped at runtime without duplicating a single class name.
        // The variables hold space-separated sRGB channels — see index.css.
        //
        // Deliberately NOT indigo/violet: that is the loudest AI-design tell.
        // The accent is a single burnt sienna, and `primary` is ink itself.
        primary: "rgb(var(--s-primary) / <alpha-value>)",
        "on-primary": "rgb(var(--s-on-primary) / <alpha-value>)",
        "primary-container": "rgb(var(--s-primary-container) / <alpha-value>)",
        "on-primary-container": "rgb(var(--s-on-primary-container) / <alpha-value>)",
        "primary-fixed": "rgb(var(--s-primary-fixed) / <alpha-value>)",
        "primary-fixed-dim": "rgb(var(--s-primary-fixed-dim) / <alpha-value>)",
        "on-primary-fixed": "rgb(var(--s-on-primary-fixed) / <alpha-value>)",
        "on-primary-fixed-variant": "rgb(var(--s-on-primary-fixed-variant) / <alpha-value>)",
        "surface-tint": "rgb(var(--s-surface-tint) / <alpha-value>)",

        // The one colour moment. Links, emphasis, and the in-progress state.
        accent: "rgb(var(--s-accent) / <alpha-value>)",
        "on-accent": "rgb(var(--s-on-accent) / <alpha-value>)",
        "accent-container": "rgb(var(--s-accent-container) / <alpha-value>)",
        "on-accent-container": "rgb(var(--s-on-accent-container) / <alpha-value>)",

        secondary: "rgb(var(--s-secondary) / <alpha-value>)",
        "on-secondary": "rgb(var(--s-on-secondary) / <alpha-value>)",
        "secondary-container": "rgb(var(--s-secondary-container) / <alpha-value>)",
        "on-secondary-container": "rgb(var(--s-on-secondary-container) / <alpha-value>)",
        "secondary-fixed": "rgb(var(--s-secondary-fixed) / <alpha-value>)",
        "secondary-fixed-dim": "rgb(var(--s-secondary-fixed-dim) / <alpha-value>)",
        "on-secondary-fixed": "rgb(var(--s-on-secondary-fixed) / <alpha-value>)",
        "on-secondary-fixed-variant": "rgb(var(--s-on-secondary-fixed-variant) / <alpha-value>)",

        tertiary: "rgb(var(--s-tertiary) / <alpha-value>)",
        "on-tertiary": "rgb(var(--s-on-tertiary) / <alpha-value>)",
        "tertiary-container": "rgb(var(--s-tertiary-container) / <alpha-value>)",
        "on-tertiary-container": "rgb(var(--s-on-tertiary-container) / <alpha-value>)",
        "tertiary-fixed": "rgb(var(--s-tertiary-fixed) / <alpha-value>)",
        "tertiary-fixed-dim": "rgb(var(--s-tertiary-fixed-dim) / <alpha-value>)",
        "on-tertiary-fixed": "rgb(var(--s-on-tertiary-fixed) / <alpha-value>)",
        "on-tertiary-fixed-variant": "rgb(var(--s-on-tertiary-fixed-variant) / <alpha-value>)",

        error: "rgb(var(--s-error) / <alpha-value>)",
        "on-error": "rgb(var(--s-on-error) / <alpha-value>)",
        "error-container": "rgb(var(--s-error-container) / <alpha-value>)",
        "on-error-container": "rgb(var(--s-on-error-container) / <alpha-value>)",

        background: "rgb(var(--s-background) / <alpha-value>)",
        "on-background": "rgb(var(--s-on-background) / <alpha-value>)",
        surface: "rgb(var(--s-surface) / <alpha-value>)",
        "on-surface": "rgb(var(--s-on-surface) / <alpha-value>)",
        "surface-variant": "rgb(var(--s-surface-variant) / <alpha-value>)",
        "on-surface-variant": "rgb(var(--s-on-surface-variant) / <alpha-value>)",
        "surface-container-lowest": "rgb(var(--s-surface-container-lowest) / <alpha-value>)",
        "surface-container-low": "rgb(var(--s-surface-container-low) / <alpha-value>)",
        "surface-container": "rgb(var(--s-surface-container) / <alpha-value>)",
        "surface-container-high": "rgb(var(--s-surface-container-high) / <alpha-value>)",
        "surface-container-highest": "rgb(var(--s-surface-container-highest) / <alpha-value>)",
        "surface-dim": "rgb(var(--s-surface-dim) / <alpha-value>)",
        "surface-bright": "rgb(var(--s-surface-bright) / <alpha-value>)",

        outline: "rgb(var(--s-outline) / <alpha-value>)",
        "outline-variant": "rgb(var(--s-outline-variant) / <alpha-value>)",

        "inverse-surface": "rgb(var(--s-inverse-surface) / <alpha-value>)",
        "inverse-on-surface": "rgb(var(--s-inverse-on-surface) / <alpha-value>)",
        "inverse-primary": "rgb(var(--s-inverse-primary) / <alpha-value>)",
      },

      // Tight, letterpress-ish corners. Big radii + pills everywhere is one of
      // the more recognisable AI-design signatures.
      borderRadius: {
        DEFAULT: "0.25rem",
        xs: "0.125rem",
        sm: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.5rem",
        full: "9999px",
      },

      spacing: {
        unit: "4px",
        "margin-mobile": "20px",
        "margin-desktop": "48px",
        gutter: "24px",
        "container-max": "1180px",
        "reading-max": "46rem",
        "section-gap": "80px",
        "sidebar-w": "17.5rem",
        "rail-h": "3.75rem",
      },

      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "Cambria", "serif"],
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        // Legacy aliases kept so existing utility names keep resolving.
        "label-sm": ["Inter", "sans-serif"],
        "display-lg": ['"Source Serif 4"', "serif"],
        "display-lg-mobile": ['"Source Serif 4"', "serif"],
        "headline-md": ['"Source Serif 4"', "serif"],
        "body-lg": ["Inter", "sans-serif"],
        "body-md": ["Inter", "sans-serif"],
        "mono-ui": ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },

      fontSize: {
        "label-sm": [
          "13px",
          { lineHeight: "16px", letterSpacing: "0.02em", fontWeight: "500" },
        ],
        "label-xs": [
          "11px",
          { lineHeight: "14px", letterSpacing: "0.1em", fontWeight: "600" },
        ],
        "display-lg": [
          "clamp(2.5rem, 6vw, 4rem)",
          {
            lineHeight: "1.08",
            letterSpacing: "-0.025em",
            fontWeight: "600",
          },
        ],
        "display-lg-mobile": [
          "2.25rem",
          { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "600" },
        ],
        "mono-ui": ["12.5px", { lineHeight: "1.55", fontWeight: "400" }],
        "headline-md": [
          "1.5rem",
          { lineHeight: "1.95rem", letterSpacing: "-0.01em", fontWeight: "600" },
        ],
        "headline-sm": [
          "1.125rem",
          { lineHeight: "1.6rem", letterSpacing: "-0.005em", fontWeight: "600" },
        ],
        "body-lg": [
          "1.125rem",
          { lineHeight: "1.7", fontWeight: "400" },
        ],
        "body-md": [
          "1rem",
          { lineHeight: "1.65", fontWeight: "400" },
        ],
        "body-sm": [
          "0.875rem",
          { lineHeight: "1.55", fontWeight: "400" },
        ],
      },
      // No soft drop shadows. Separation comes from hairlines and tonal steps —
      // `0.1 opacity shadow` on every card is another AI-design fingerprint.
      boxShadow: {
        none: "none",
        hairline: "inset 0 0 0 1px rgb(var(--s-outline-variant) / 0.9)",
        "focus-ring": "0 0 0 3px rgb(var(--s-accent) / 0.18)",
        "press": "inset 0 2px 0 rgb(var(--s-shadow) / 0.12)",
      },

      keyframes: {
        "fade-rise": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "none" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "fade-scale": {
          "0%": { opacity: "0", transform: "scale(.97)" },
          "100%": { opacity: "1", transform: "none" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "none" },
        },
        "pulse-opacity": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        "halo": {
          "0%": { transform: "scale(.85)", opacity: "0.7" },
          "70%": { transform: "scale(1.9)", opacity: "0" },
          "100%": { transform: "scale(1.9)", opacity: "0" },
        },
        "sheen": {
          "0%": { transform: "translateX(-120%)" },
          "100%": { transform: "translateX(120%)" },
        },
        "caret-blink": {
          "0%, 45%": { opacity: "1" },
          "50%, 95%": { opacity: "0.15" },
          "100%": { opacity: "1" },
        },
        "shimmer": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "draw-check": {
          "0%": { strokeDashoffset: "24" },
          "100%": { strokeDashoffset: "0" },
        },
        "rise-draw": {
          "0%": { transform: "scaleY(0)" },
          "100%": { transform: "scaleY(1)" },
        },
        "pop": {
          "0%": { transform: "scale(.9)", opacity: "0" },
          "60%": { transform: "scale(1.04)" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },

      animation: {
        "status-pulse": "pulse-opacity 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-rise": "fade-rise .5s cubic-bezier(.22,1,.36,1) both",
        "fade-in": "fade-in .45s ease-out both",
        "fade-scale": "fade-scale .35s cubic-bezier(.22,1,.36,1) both",
        "slide-in-right": "slide-in-right .3s cubic-bezier(.22,1,.36,1) both",
        halo: "halo 2.4s cubic-bezier(.4,0,.6,1) infinite",
        caret: "caret-blink 1.1s steps(1) infinite",
        shimmer: "shimmer 1.8s cubic-bezier(.4,0,.6,1) infinite",
        "spin-slow": "spin-slow 2.6s linear infinite",
        "draw-check": "draw-check .5s cubic-bezier(.22,1,.36,1) both",
        "rise-draw": "rise-draw .6s cubic-bezier(.22,1,.36,1) both",
        pop: "pop .3s cubic-bezier(.22,1,.36,1) both",
      },
    },
  },
  plugins: [],
};
