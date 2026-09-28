import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ScribeLogo } from "./ScribeLogo";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "../context/AuthContext";

// Header used on public marketing/auth pages. When the viewer is signed in we
// swap the brand target to /chat so clicking the logo doesn't bounce them
// through the now-restricted landing page.
export const Header: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();
  const brandTo = isAuthenticated ? "/chat" : "/";
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      data-print-hide
      className={`sticky top-0 z-50 w-full border-b transition-colors duration-200 ${
        scrolled
          ? "border-outline-variant bg-background"
          : "border-transparent bg-background"
      }`}
    >
      <div className="mx-auto flex h-rail-h w-full max-w-container-max items-center justify-between px-margin-mobile md:px-margin-desktop">
        <Link
          to={brandTo}
          aria-label="Scribe home"
          className="group -ml-1 flex items-center rounded px-1 py-1 text-on-surface transition-transform duration-200 hover:-translate-y-px"
        >
          <ScribeLogo className="h-6 text-accent text-[1.35rem] transition-colors duration-200 group-hover:text-accent-fixed-dim" />
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {isAuthenticated ? (
            <>
              <Link
                to="/chat"
                className="link-underline hidden rounded px-3 py-2 font-label-sm text-label-sm text-on-surface-variant transition-colors duration-200 hover:text-on-surface sm:block"
              >
                Open Chat
              </Link>
              <button
                onClick={logout}
                className="btn btn-ghost px-3 py-2"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="link-underline hidden rounded px-3 py-2 font-label-sm text-label-sm text-on-surface-variant transition-colors duration-200 hover:text-on-surface sm:block"
              >
                Log in
              </Link>
              <Link to="/signup" className="btn btn-primary btn-sheen px-5 py-2.5">
                Sign up
                <span className="material-symbols-outlined text-[18px]">
                  arrow_forward
                </span>
              </Link>
            </>
          )}
          <ThemeToggle className="ml-1" />
        </nav>
      </div>
    </header>
  );
};
