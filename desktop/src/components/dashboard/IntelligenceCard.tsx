import React from 'react';
import { useApp } from '../../context/AppContext';
import { ProviderStatus } from '../../types/intelligence';
import { ArrowUpRight, CheckCircle2, Cpu, MessageSquare, Server, Sparkles, XCircle, Zap } from 'lucide-react';

interface IntelligenceCardProps {
  providers: ProviderStatus[];
  totalModels: number;
  onNavigateToChat: () => void;
}

export const IntelligenceCard: React.FC<IntelligenceCardProps> = ({
  providers,
  totalModels,
  onNavigateToChat,
}) => {
  const { intelligenceStatus } = useApp();

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Intelligence Centre</h3>
              <p className="text-[11px] text-slate-400">Universal Model Routing & Execution</p>
            </div>
          </div>

          <button
            onClick={onNavigateToChat}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 transition-all group"
          >
            <span>Open Chat</span>
            <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>

        {/* Core Stats Overview */}
        <div className="grid grid-cols-3 gap-2.5 mb-4">
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block mb-0.5">Primary Model</span>
            <span className="text-xs font-mono font-semibold text-cyan-300 truncate block">
              {intelligenceStatus?.default_model || 'safe_orchestrator'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block mb-0.5">Available Models</span>
            <span className="text-xs font-bold text-slate-200">
              {totalModels > 0 ? totalModels : intelligenceStatus?.total_available_models || 1} Registered
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block mb-0.5">Active Providers</span>
            <span className="text-xs font-bold text-slate-200">
              {intelligenceStatus?.active_providers_count || providers.filter(p => p.is_available).length} Online
            </span>
          </div>
        </div>

        {/* Provider Connectivity Table */}
        <div className="space-y-1.5 mb-2">
          <span className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider block px-1">
            Provider Health & Latency
          </span>
          <div className="space-y-1.5">
            {providers.length === 0 ? (
              <div className="p-2.5 rounded-xl bg-background-tertiary text-center text-xs text-slate-500">
                Loading AI providers...
              </div>
            ) : (
              providers.map((p) => (
                <div
                  key={p.provider_id}
                  className="flex items-center justify-between p-2 rounded-xl bg-background-tertiary/50 border border-border-subtle/70 text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {p.is_available ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                    )}
                    <span className="font-semibold text-slate-200 truncate">{p.name}</span>
                    {p.is_local && (
                      <span className="px-1 py-0.2 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        LOCAL
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 font-mono text-[11px]">
                    {p.latency_ms !== null && p.latency_ms !== undefined && (
                      <span className="text-slate-400">{Math.round(p.latency_ms)}ms</span>
                    )}
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        p.is_available
                          ? 'bg-emerald-500/15 text-emerald-300'
                          : 'bg-rose-500/15 text-rose-300'
                      }`}
                    >
                      {p.is_available ? 'Available' : 'Offline'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60 mt-2">
        <span>Routing Policy: <strong className="text-slate-300 uppercase">{intelligenceStatus?.routing_preference || 'Balanced'}</strong></span>
        <span>Credentials: <strong className="text-emerald-400">Encrypted in Vault</strong></span>
      </div>
    </div>
  );
};
