import React from 'react';
import { useApp } from '../../context/AppContext';
import { StatusBadge } from '../layout/StatusBadge';
import { Activity, Clock, Cpu, Database, RefreshCw, Shield, Zap } from 'lucide-react';

interface IdentityStateCardProps {
  lastUpdated: Date | null;
  isLoading: boolean;
  onRefresh: () => void;
  uptimeSeconds: number;
  onNavigate: (view: 'chat' | 'work' | 'memory' | 'voice' | 'settings') => void;
}

export const IdentityStateCard: React.FC<IdentityStateCardProps> = ({
  lastUpdated,
  isLoading,
  onRefresh,
  uptimeSeconds,
  onNavigate,
}) => {
  const { assistantState, intelligenceStatus, backendOnline, activeConversationId } = useApp();

  const formatUptime = (secs: number) => {
    const d = Math.floor(secs / 86400);
    const h = Math.floor((secs % 86400) / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md relative overflow-hidden flex flex-col justify-between">
      {/* Subtle background glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl -z-10 pointer-events-none" />

      {/* Top Header */}
      <div>
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
              <span className="font-extrabold text-sm tracking-wider text-white">LOVE</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100 tracking-tight">LOVE Command Core</h2>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
                  SOVEREIGN AI
                </span>
              </div>
              <p className="text-xs text-slate-400">Personal AI Assistant System Observability</p>
            </div>
          </div>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 rounded-xl bg-background-tertiary border border-border-subtle hover:border-cyan-500/40 text-slate-400 hover:text-cyan-300 transition-all shadow-sm"
            title="Refresh All Dashboard Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>

        {/* Status Indicator Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">State</span>
            <StatusBadge state={assistantState} />
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Backend</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${backendOnline ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-rose-500'}`} />
              <span className="text-xs font-semibold text-slate-200">
                {backendOnline ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Routing Mode</span>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200 capitalize">
                {intelligenceStatus?.routing_preference || 'Balanced'}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Process Uptime</span>
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs font-mono text-slate-200">{formatUptime(uptimeSeconds)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info & Active Session */}
      <div className="pt-3 border-t border-border-subtle/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-2">
          <span>Active Model:</span>
          <span className="px-2 py-0.5 rounded bg-background-tertiary text-cyan-300 font-mono text-[10px] border border-border-subtle">
            {intelligenceStatus?.default_model || 'safe_orchestrator'}
          </span>
          {intelligenceStatus?.local_only_mode && (
            <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold">
              LOCAL ONLY
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 font-mono text-[10px] text-slate-500">
          <Clock className="w-3 h-3" />
          <span>Updated {lastUpdated ? lastUpdated.toLocaleTimeString() : 'connecting...'}</span>
        </div>
      </div>
    </div>
  );
};
