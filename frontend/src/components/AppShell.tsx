import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ScribeLogo } from "./ScribeLogo";

// Layout shell used by /chat, /reports and /report/:reportId. Provides the
// persistent sidebar with a mobile toggle.
export const AppShell: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const scrollRef = useRef<HTMLElement | null>(null);

  // Each route should start at the top of its own scroll container.
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [location.pathname]);

  // Lock the page behind the mobile drawer.
  useEffect(() => {
    if (!mobileOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-on-surface antialiased">
      {/* Mobile top bar */}
      <div className="fixed left-0 top-0 z-50 flex h-rail-h w-full items-center justify-between border-b border-outline-variant bg-surface px-4 md:hidden">
        <a
          href="/chat"
          aria-label="Scribe home"
          className="flex items-center text-on-surface"
        >
          <ScribeLogo className="h-[1.3rem] text-accent text-[1.3rem]" />
        </a>
        <button
          onClick={() => setMobileOpen((v) => !v)}
          className="btn btn-ghost h-9 w-9 !rounded-sm !p-0 text-[20px]"
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
        >
          <span className="material-symbols-outlined text-[22px]">
            {mobileOpen ? "close" : "menu"}
          </span>
        </button>
      </div>

      <Sidebar
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <main
        ref={scrollRef}
        className="min-h-screen flex-1 overflow-y-auto bg-background pt-rail-h md:ml-sidebar-w md:pt-0"
      >
        {children}
      </main>
    </div>
  );
};
