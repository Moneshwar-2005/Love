import React from 'react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { StatusBadge } from './StatusBadge';
import {
  AlertTriangle,
  Cpu,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  User as UserIcon,
} from 'lucide-react';

interface HeaderProps {
  onOpenSystemStatus: () => void;
  onOpenSettings: () => void;
  onToggleMobileNav?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSystemStatus,
  onOpenSettings,
  onToggleMobileNav,
}) => {
  const { user, logout } = useAuth();
  const {
    assistantState,
    intelligenceStatus,
    pendingApprovalsCount,
    setCurrentView,
  } = useApp();

  const defaultModelName = intelligenceStatus
    ? `${intelligenceStatus.active_provider} (${intelligenceStatus.active_model})`
    : 'Connecting...';

  return (
    <header className="h-14 border-b border-border-subtle bg-background-secondary/90 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between select-none z-20 sticky top-0">
      {/* Left: Mobile Menu Toggle + Brand Identity & Status */}
      <div className="flex items-center gap-2 sm:gap-4">
        {onToggleMobileNav && (
          <button
            type="button"
            onClick={onToggleMobileNav}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-background-tertiary md:hidden transition"
            aria-label="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <span className="font-bold text-xs tracking-wider text-white">L</span>
          </div>
          <span className="font-bold tracking-tight text-slate-100 text-sm hidden sm:inline">
            LOVE <span className="text-[10px] text-cyan-400 font-mono font-normal">Web v1.0</span>
          </span>
        </div>

        <StatusBadge state={assistantState} />
      </div>

      {/* Center: System Routing & Hardware Status */}
      <div className="hidden lg:flex items-center gap-2">
        <button
          onClick={onOpenSystemStatus}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-background-tertiary/70 text-slate-300 hover:text-cyan-400 hover:bg-background-tertiary border border-border-subtle transition-colors"
          title="Inspect Model Status & Hardware Routing"
        >
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span className="max-w-[160px] truncate">{defaultModelName}</span>
        </button>

        {intelligenceStatus?.local_only_mode && (
          <div
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            title="Strict Local Privacy Mode Active"
          >
            <ShieldCheck className="w-3 h-3" />
            <span>Local Sovereign</span>
          </div>
        )}
      </div>

      {/* Right: Actions, Alerts, User & Settings */}
      <div className="flex items-center gap-2">
        {pendingApprovalsCount > 0 && (
          <button
            onClick={() => setCurrentView('work')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30 transition animate-pulse"
            title={`${pendingApprovalsCount} pending tool approvals require review`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden xs:inline">Approvals</span>
            <span className="bg-rose-500 text-white rounded-full px-1.5 py-0.2 text-[10px] font-bold">
              {pendingApprovalsCount}
            </span>
          </button>
        )}

        <button
          onClick={onOpenSettings}
          className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-background-tertiary transition"
          title="Settings & Cross-Device Sync"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>

        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-border-subtle">
            <div className="flex items-center gap-1.5 text-xs text-slate-300 font-medium">
              <div className="w-6 h-6 rounded-full bg-cyan-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-300 text-[10px]">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <span className="hidden sm:inline max-w-[90px] truncate">{user.username}</span>
            </div>

            <button
              onClick={() => logout()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-background-tertiary transition"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
