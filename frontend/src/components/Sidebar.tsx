import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";
import { ScribeLogo } from "./ScribeLogo";
import { ThemeToggle } from "./ThemeToggle";

interface ChatSummary {
  conversation_id: string;
  title: string;
  updated_at: string;
}

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  onCloseMobile,
}) => {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    apiRequest("/chats/all", { token })
      .then((data) => {
        if (cancelled) return;
        setChats(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!cancelled) setChats([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleNewResearch = () => {
    onCloseMobile();
    navigate("/chat");
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleLibrary = () => {
    onCloseMobile();
    navigate("/reports");
  };

  const isOnChat = location.pathname.startsWith("/chat");
  const isOnReports = location.pathname.startsWith("/report/");
  const isOnLibrary = location.pathname === "/reports";

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="animate-fade-in fixed inset-0 z-30 bg-inverse-surface/45 md:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        data-print-hide
        className={`fixed left-0 top-0 z-40 flex h-full w-sidebar-w flex-col border-r border-outline-variant bg-surface transition-transform duration-300 ease-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        {/* Brand */}
        <div className="flex items-center justify-between gap-2 px-5 pb-5 pt-6">
          <Link
            to="/chat"
            onClick={onCloseMobile}
            aria-label="Scribe home"
            className="group -ml-1 flex items-center rounded px-1 py-0.5 text-on-surface"
          >
            <ScribeLogo className="h-[1.35rem] text-accent text-[1.35rem] transition-transform duration-200 group-hover:-translate-y-px" />
          </Link>
          <button
            onClick={onCloseMobile}
            className="btn btn-ghost h-8 w-8 !rounded-sm !p-0 text-[20px] md:hidden"
            aria-label="Close menu"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Primary action */}
        <div className="px-4 pb-5">
          <button onClick={handleNewResearch} className="btn btn-primary btn-sheen w-full py-3">
            <span className="material-symbols-outlined text-[18px]">add</span>
            New research
          </button>
        </div>

        {/* Main navigation */}
        <nav className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-3 pb-4">
          <div className="flex flex-col gap-1">
            <SectionLabel>Workspace</SectionLabel>
            <NavItem
              icon="forum"
              label="Research"
              active={isOnChat || isOnReports}
              onClick={handleNewResearch}
            />
            <NavItem
              icon="library_books"
              label="Library"
              active={isOnLibrary}
              onClick={handleLibrary}
              trailing={
                !loading && chats.length > 0 ? (
                  <span className="ml-auto rounded-full bg-surface-container-high px-1.5 py-0.5 text-[11px] tabular-nums text-on-surface-variant">
                    {chats.length}
                  </span>
                ) : null
              }
            />
          </div>

          <div className="flex min-h-0 flex-col">
            <SectionLabel>Recent chats</SectionLabel>
            {loading ? (
              <div className="flex flex-col gap-1.5 px-1 pt-1">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="skeleton h-8 w-full" />
                ))}
              </div>
            ) : chats.length === 0 ? (
              <p className="px-3 py-2 font-body-sm text-body-sm text-on-surface-variant opacity-70">
                No chats yet. Ask Scribe something to start one.
              </p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {chats.map((c) => {
                  const isActive =
                    location.pathname === `/chat/${c.conversation_id}`;
                  return (
                    <Link
                      key={c.conversation_id}
                      to={`/chat/${c.conversation_id}`}
                      onClick={onCloseMobile}
                      title={c.title || "Untitled chat"}
                      className={`group flex animate-fade-in items-center gap-2.5 rounded-md px-3 py-2 font-body-sm text-body-sm transition-[background-color,color,transform] duration-200 hover:translate-x-0.5 ${
                        isActive
                          ? "bg-primary-container text-on-primary-container"
                          : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                      }`}
                    >
                      <span
                        className={`material-symbols-outlined shrink-0 text-[16px] ${
                          isActive ? "text-accent" : "text-outline"
                        }`}
                      >
                        chat_bubble
                      </span>
                      <span className="truncate">{c.title || "Untitled chat"}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </nav>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 border-t border-outline-variant px-4 py-3">
          <ThemeToggle className="text-[20px]" />
          <button
            onClick={handleLogout}
            className="btn btn-ghost flex-1 justify-start px-3 py-2 text-on-surface-variant hover:text-error"
          >
            <span className="material-symbols-outlined text-[20px]">
              logout
            </span>
            <span>Log out</span>
          </button>
        </div>
      </aside>
    </>
  );
};

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="px-3 pb-2 pt-1 font-label-sm text-[11px] font-semibold uppercase tracking-[0.12em] text-outline">
    {children}
  </p>
);

const NavItem: React.FC<{
  icon: string;
  label: string;
  active?: boolean;
  onClick?: () => void;
  trailing?: React.ReactNode;
}> = ({ icon, label, active, onClick, trailing }) => (
  <button
    onClick={onClick}
    aria-current={active ? "page" : undefined}
    className={`group flex items-center gap-2.5 rounded-sm px-3 py-2.5 text-left font-label-sm text-label-sm transition-colors duration-150 ${
      active
        ? "bg-primary-container font-semibold text-on-primary-container"
        : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
    }`}
  >
    <span
      className={`material-symbols-outlined text-[20px] transition-colors duration-150 ${
        active ? "text-accent" : "text-outline group-hover:text-accent"
      }`}
    >
      {icon}
    </span>
    <span>{label}</span>
    {trailing}
  </button>
);
