import React, { useEffect, useState } from 'react';
import { useMobileApp } from '../../context/AppContext';
import { MemoryCategory, MemoryEntry, MemorySuggestion } from '../../types/memory';
import { mobileMemoryService } from '../../services/memoryService';
import { Brain, Check, RefreshCw, Search, Sparkles, Trash2, X } from 'lucide-react';

export const MobileMemoryWorkspace: React.FC = () => {
  const { pendingSuggestionsCount, refreshCounts } = useMobileApp();
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [suggestions, setSuggestions] = useState<MemorySuggestion[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<MemoryCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'memories' | 'suggestions'>('memories');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const categories: Array<{ id: MemoryCategory | 'all'; label: string }> = [
    { id: 'all', label: 'All' },
    { id: 'core', label: 'Core' },
    { id: 'preferences', label: 'Preferences' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'episodic', label: 'Episodic' },
    { id: 'contacts', label: 'Contacts' },
  ];

  const loadData = async () => {
    setIsLoading(true);
    try {
      const cat = selectedCategory === 'all' ? undefined : selectedCategory;
      const [mList, sList] = await Promise.allSettled([
        mobileMemoryService.listMemories(cat, searchQuery),
        mobileMemoryService.listSuggestions('pending'),
      ]);
      if (mList.status === 'fulfilled') setMemories(mList.value);
      if (sList.status === 'fulfilled') setSuggestions(sList.value);
      await refreshCounts();
    } catch (err) {
      console.warn('Memory load error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCategory]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const handleResolveSuggestion = async (suggestionId: string, approved: boolean) => {
    try {
      await mobileMemoryService.resolveSuggestion(suggestionId, approved);
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
      await refreshCounts();
      await loadData();
    } catch (err) {
      console.warn('Suggestion resolution error:', err);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await mobileMemoryService.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      console.warn('Delete memory error:', err);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background">
      {/* Sub-Header & Segmented Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex bg-background-secondary p-1 rounded-xl border border-border-subtle">
          <button
            onClick={() => setActiveTab('memories')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              activeTab === 'memories'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Memories ({memories.length})
          </button>

          <button
            onClick={() => setActiveTab('suggestions')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === 'suggestions'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Consent Queue</span>
            {pendingSuggestionsCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] font-bold ${
                activeTab === 'suggestions' ? 'bg-slate-950 text-cyan-400' : 'bg-rose-500 text-white'
              }`}>
                {pendingSuggestionsCount}
              </span>
            )}
          </button>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          aria-label="Refresh memory data"
          className="p-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-400 hover:text-cyan-400 transition"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* MEMORIES VIEW */}
      {activeTab === 'memories' && (
        <div className="space-y-3">
          {/* Search bar */}
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search episodic memories..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-background-secondary border border-border-subtle text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </form>

          {/* Category Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scrollbar">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold whitespace-nowrap transition ${
                  selectedCategory === cat.id
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                    : 'bg-background-secondary text-slate-400 border border-border-subtle hover:text-white'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* List */}
          {memories.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <Brain className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-300">No Memories Found</h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Personal facts, user preferences, and episodic knowledge will be preserved here.
              </p>
            </div>
          ) : (
            memories.map((entry) => (
              <div
                key={entry.id}
                className="p-3.5 rounded-2xl bg-background-secondary border border-border-subtle space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-cyan-400 font-mono tracking-wider">
                    {entry.category}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 font-mono">
                      ⭐ {entry.importance || 1}
                    </span>
                    <button
                      onClick={() => handleDeleteMemory(entry.id)}
                      aria-label="Delete memory"
                      className="text-slate-500 hover:text-rose-400 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <div className="text-xs font-semibold text-slate-200">{entry.key}</div>
                <p className="text-xs text-slate-300 whitespace-pre-wrap">{entry.value}</p>
                {entry.tags && entry.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {entry.tags.map((t, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.2 rounded text-[9px] bg-background-tertiary text-slate-400 font-mono"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* SUGGESTIONS VIEW (Explicit Consent Queue) */}
      {activeTab === 'suggestions' && (
        <div className="space-y-3">
          {suggestions.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <Sparkles className="w-10 h-10 text-cyan-400/50 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-300">Consent Queue Empty</h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                When LOVE infers new memories from conversations, they wait here for your explicit consent.
              </p>
            </div>
          ) : (
            suggestions.map((sug) => (
              <div
                key={sug.id}
                className="p-4 rounded-2xl bg-background-secondary border border-cyan-500/30 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-bold">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Inferred Knowledge</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">{sug.category}</span>
                </div>

                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-white">{sug.key}</h4>
                  <p className="text-xs text-slate-300 bg-background-tertiary p-2 rounded-xl border border-border-subtle">
                    {sug.value}
                  </p>
                </div>

                <p className="text-[11px] text-slate-400 italic">Reason: {sug.reason}</p>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => handleResolveSuggestion(sug.id, false)}
                    className="flex-1 py-2 rounded-xl bg-background-tertiary border border-border-subtle hover:bg-rose-500/20 text-rose-400 font-semibold text-xs flex items-center justify-center gap-1.5 transition"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Discard</span>
                  </button>
                  <button
                    onClick={() => handleResolveSuggestion(sug.id, true)}
                    className="flex-1 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition shadow-lg shadow-cyan-500/20"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Save to Memory</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
