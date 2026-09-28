import React, { useEffect, useState } from "react";

const STORAGE_KEY = "scribe-theme";
type Theme = "paper" | "ink";

const readTheme = (): Theme => {
  if (typeof document === "undefined") return "paper";
  const attr = document.documentElement.getAttribute("data-theme");
  return attr === "ink" ? "ink" : "paper";
};

// Small sun/moon cross-fade. Sizes are inherited from the button's font-size
// so callers control it with a text-* class.
export const ThemeToggle: React.FC<{ className?: string }> = ({
  className = "",
}) => {
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const isInk = theme === "ink";

  const toggle = () => {
    const next: Theme = isInk ? "paper" : "ink";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private mode — the theme just won't persist */
    }
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isInk ? "Switch to light theme" : "Switch to dark theme"}
      title={isInk ? "Light theme" : "Dark theme"}
      className={`btn btn-ghost h-9 w-9 !rounded-full p-0 text-[20px] ${className}`}
    >
      <span className="relative block h-5 w-5">
        {/* Keep both glyphs mounted and cross-fade them so the swap animates. */}
        <span
          className={`material-symbols-outlined absolute inset-0 flex items-center justify-center text-[20px] transition-[opacity,transform] duration-300 ease-out ${
            mounted && isInk
              ? "opacity-100 scale-100 rotate-0"
              : "opacity-0 scale-50 -rotate-90"
          }`}
        >
          dark_mode
        </span>
        <span
          className={`material-symbols-outlined absolute inset-0 flex items-center justify-center text-[20px] transition-[opacity,transform] duration-300 ease-out ${
            mounted && !isInk
              ? "opacity-100 scale-100 rotate-0"
              : "opacity-0 scale-50 rotate-90"
          }`}
        >
          light_mode
        </span>
      </span>
    </button>
  );
};
