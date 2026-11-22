import React from 'react';
import { useMobileApp } from '../../context/AppContext';
import { Wifi, WifiOff } from 'lucide-react';

interface MobileHeaderProps {
  title: string;
  leftAction?: React.ReactNode;
  rightAction?: React.ReactNode;
}

export const MobileHeader: React.FC<MobileHeaderProps> = ({
  title,
  leftAction,
  rightAction,
}) => {
  const { backendOnline, assistantState } = useMobileApp();

  return (
    <header className="h-14 bg-background-secondary/90 backdrop-blur-md border-b border-border-subtle flex items-center justify-between px-4 z-30 shrink-0">
      <div className="flex items-center gap-2.5 min-w-0">
        {leftAction}
        <div className="flex items-center gap-2 min-w-0">
          <div className="relative flex items-center justify-center w-7 h-7 rounded-xl bg-cyan-500/10 border border-cyan-500/30 shrink-0">
            <span className="text-cyan-400 font-bold text-xs">L</span>
            <span
              className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background-secondary ${
                backendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-slate-100 truncate">{title}</h1>
            <div className="text-[10px] text-slate-400 capitalize flex items-center gap-1 font-mono">
              <span>{assistantState}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {rightAction}
        <div
          title={backendOnline ? 'Backend Online' : 'Backend Offline'}
          className={`p-1.5 rounded-lg border text-xs flex items-center ${
            backendOnline
              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
              : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
          }`}
        >
          {backendOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
        </div>
      </div>
    </header>
  );
};
