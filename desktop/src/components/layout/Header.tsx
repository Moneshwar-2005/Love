import React from 'react';
import { useApp } from '../../context/AppContext';
import { StatusBadge } from './StatusBadge';
import { AlertTriangle, Cpu, Minus, ShieldCheck, Square, X } from 'lucide-react';

interface HeaderProps {
  onOpenSystemStatus: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSystemStatus }) => {
  const {
    assistantState,
    intelligenceStatus,
    pendingApprovalsCount,
    setCurrentView,
  } = useApp();

  const isElectron = typeof window !== 'undefined' && !!window.loveDesktop?.isElectron;

  const handleMinimize = () => {
    window.loveDesktop?.windowControls.minimize();
  };

  const handleMaximize = () => {
    window.loveDesktop?.windowControls.maximize();
  };

  const handleClose = () => {
    window.loveDesktop?.windowControls.close();
  };

  const defaultModelName = intelligenceStatus
    ? `${intelligenceStatus.default_provider}`
    : 'Connecting...';

  return (
    <header className="h-14 border-b border-border-subtle bg-background-secondary/80 backdrop-blur-md px-4 flex items-center justify-between select-none z-20">
      {/* Left: Brand Identity & Assistant Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <span className="font-bold text-xs tracking-wider text-white">L</span>
          </div>
          <span className="font-bold tracking-tight text-slate-100 text-sm hidden sm:inline">
            LOVE <span className="text-[10px] text-cyan-400 font-mono font-normal">v1.0</span>
          </span>
        </div>

        <StatusBadge state={assistantState} />
      </div>

      {/* Center: System Routing & Hardware Status */}
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenSystemStatus}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-background-tertiary/70 text-slate-300 hover:text-cyan-400 hover:bg-background-tertiary border border-border-subtle transition-colors"
          title="Inspect Model Status & Hardware Routing"
        >
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span className="max-w-[140px] truncate">{defaultModelName}</span>
          {intelligenceStatus?.local_only_mode && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              LOCAL
            </span>
          )}
        </button>

        {pendingApprovalsCount > 0 && (
          <button
            onClick={() => setCurrentView('work')}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/40 hover:bg-rose-500/25 animate-pulse transition-all"
            title={`${pendingApprovalsCount} pending tool approvals requiring user authorization`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>{pendingApprovalsCount} Approval{pendingApprovalsCount > 1 ? 's' : ''}</span>
          </button>
        )}
      </div>

      {/* Right: Window Controls for Electron Desktop */}
      <div className="flex items-center gap-2">
        {isElectron && (
          <div className="flex items-center gap-1 border-l border-border-subtle pl-2">
            <button
              onClick={handleMinimize}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
              title="Minimize"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleMaximize}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
              title="Maximize"
            >
              <Square className="w-3 h-3" />
            </button>
            <button
              onClick={handleClose}
              className="p-1.5 rounded hover:bg-rose-600 text-slate-400 hover:text-white transition-colors"
              title="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
