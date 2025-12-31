import React, { useCallback } from "react";
import {
  MicIcon,
  DashboardIcon,
  DescriptionIcon,
  CodeIcon,
  SettingsIcon,
} from "../assets/Icons";

type NavItem = "overview" | "transcriptions" | "snippets" | "settings";

interface SessionStats {
  duration: string;
  words: number;
  confidence: string;
  confidencePercent: number;
}

interface SidebarProps {
  sessionStats: SessionStats;
  activeNav?: NavItem;
  onNavChange?: (nav: NavItem) => void;
  onOpenSettings?: () => void;
}

// Static data at module scope - zero allocation per render
const NAV_ITEMS = [
  { id: "overview", label: "Overview", Icon: DashboardIcon },
  { id: "transcriptions", label: "Transcriptions", Icon: DescriptionIcon },
  { id: "snippets", label: "Snippets Library", Icon: CodeIcon },
  { id: "settings", label: "Settings", Icon: SettingsIcon },
] as const;

export const Sidebar: React.FC<SidebarProps> = React.memo(
  ({ sessionStats, activeNav = "overview", onNavChange, onOpenSettings }) => {
    // Single event handler using data attribute - no closure factory
    const handleNavClick = useCallback(
      (e: React.MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();
        const nav = e.currentTarget.dataset.nav as NavItem;
        if (nav === "settings") {
          onOpenSettings?.();
        } else {
          onNavChange?.(nav);
        }
      },
      [onNavChange, onOpenSettings]
    );

    return (
      <aside className="app-sidebar">
        {/* Logo / Brand */}
        <div className="sidebar-brand">
          <div className="brand-logo">
            <MicIcon />
          </div>
          <span className="brand-text">Voice2Machine</span>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ id, label, Icon }) => (
            <a
              key={id}
              href="#"
              data-nav={id}
              className={`nav-item${activeNav === id ? " active" : ""}`}
              onClick={handleNavClick}
              aria-current={activeNav === id ? "page" : undefined}
            >
              <Icon />
              <span>{label}</span>
            </a>
          ))}
        </nav>

        {/* Session Stats */}
        <div className="session-stats">
          <h3 className="stats-title">Current Session</h3>

          <div className="stat-row">
            <span className="stat-label">Duration</span>
            <span className="stat-value mono">{sessionStats.duration}</span>
          </div>

          <div className="stat-row">
            <span className="stat-label">Words</span>
            <span className="stat-value mono">{sessionStats.words}</span>
          </div>

          <div className="stat-row">
            <span className="stat-label">Confidence</span>
            <div className="confidence-meter">
              <div className="meter-track">
                <div
                  className="meter-fill"
                  style={{ width: `${sessionStats.confidencePercent}%` }}
                />
              </div>
              <span className="confidence-value">
                {sessionStats.confidence}
              </span>
            </div>
          </div>
        </div>
      </aside>
    );
  }
);

Sidebar.displayName = "Sidebar";
