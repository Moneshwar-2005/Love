import React from 'react';
import { Memory, MemoryStats } from '../../types/memory';
import { ArrowUpRight, CheckCircle, Database, FileText, Layers, ShieldAlert, Sparkles, Tag } from 'lucide-react';

interface MemorySummaryCardProps {
  stats: MemoryStats | null;
  pendingSuggestionsCount: number;
  recentMemories: Memory[];
  onNavigateToMemory: () => void;
}

export const MemorySummaryCard: React.FC<MemorySummaryCardProps> = ({
  stats,
  pendingSuggestionsCount,
  recentMemories,
  onNavigateToMemory,
}) => {
  const categories = stats?.categories_breakdown || {};
  const personalCount = categories['personal'] || 0;
  const projectCount = categories['project'] || 0;
  const conversationalCount = categories['conversational'] || 0;
  const knowledgeCount = categories['knowledge'] || 0;

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Persistent Personal Memory</h3>
              <p className="text-[11px] text-slate-400">Canonical Vector Store & Explicit Consent</p>
            </div>
          </div>

          <button
            onClick={onNavigateToMemory}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 transition-all group"
          >
            <span>Manage Memory</span>
            <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>

        {/* Pending Suggestions Warning Banner */}
        {pendingSuggestionsCount > 0 && (
          <div className="mb-3.5 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0 animate-pulse" />
              <span className="text-xs text-amber-200">
                <strong>{pendingSuggestionsCount}</strong> memory suggestion{pendingSuggestionsCount > 1 ? 's' : ''} awaiting consent
              </span>
            </div>
            <button
              onClick={onNavigateToMemory}
              className="text-[11px] font-semibold text-amber-300 hover:text-amber-100 underline decoration-amber-400"
            >
              Review Now
            </button>
          </div>
        )}

        {/* Memory Categories Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Personal</span>
            <div className="text-base font-bold text-slate-100">{personalCount}</div>
            <span className="text-[9px] text-slate-500">Preferences & Profile</span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Project</span>
            <div className="text-base font-bold text-slate-100">{projectCount}</div>
            <span className="text-[9px] text-slate-500">Code & Workspace</span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Conversational</span>
            <div className="text-base font-bold text-slate-100">{conversationalCount}</div>
            <span className="text-[9px] text-slate-500">Session Context</span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Knowledge</span>
            <div className="text-base font-bold text-slate-100">{knowledgeCount}</div>
            <span className="text-[9px] text-slate-500">Domain Facts</span>
          </div>
        </div>

        {/* Vector Retrieval Status */}
        <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle text-xs mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-300 font-medium">
              Vector Index: <strong className="text-slate-100">{stats?.vector_index_size ?? stats?.total_memories ?? 0} vectors</strong>
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
            <span>Provider: <strong className="text-emerald-300 capitalize">{stats?.embedding_provider || 'deterministic'}</strong></span>
            <span>Dim: <strong className="text-slate-300">{stats?.embedding_dimension ?? 128}</strong></span>
          </div>
        </div>

        {/* Recent Memories Preview */}
        {recentMemories.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider block px-1">
              Recent Approved Memories
            </span>
            <div className="space-y-1.5 max-h-28 overflow-y-auto custom-scrollbar pr-1">
              {recentMemories.slice(0, 3).map((mem) => (
                <div
                  key={mem.id}
                  className="p-2 rounded-xl bg-background-tertiary/40 border border-border-subtle text-xs flex items-center justify-between gap-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                        {mem.category}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(mem.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 truncate">{mem.content}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60 mt-2">
        <span>Approved Total: <strong className="text-slate-200">{stats?.total_memories || 0}</strong></span>
        <span className="text-emerald-400 font-semibold">User Consent Enforced</span>
      </div>
    </div>
  );
};
