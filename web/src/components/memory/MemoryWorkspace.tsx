import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { memoryService } from '../../services/memoryService';
import { Memory, MemoryCategory, MemorySuggestion } from '../../types/memory';
import { SuggestionCard } from './SuggestionCard';
import {
  Database,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Tag,
  Trash2,
} from 'lucide-react';

export const MemoryWorkspace: React.FC = () => {
  const { pendingSuggestionsCount, refreshPendingCounts } = useApp();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [suggestions, setSuggestions] = useState<MemorySuggestion[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<MemoryCategory | 'all'>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newContent, setNewContent] = useState<string>('');
  const [newCategory, setNewCategory] = useState<MemoryCategory>('personal');
  const [newTags, setNewTags] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [fetchedSuggestions, fetchedMemories] = await Promise.all([
        memoryService.listSuggestions('pending'),
        searchQuery.trim()
          ? memoryService.searchMemories(searchQuery.trim(), 50)
          : memoryService.listMemories({
              category: selectedCategory === 'all' ? undefined : selectedCategory,
              limit: 50,
            }),
      ]);
      setSuggestions(fetchedSuggestions);
      setMemories(fetchedMemories);
    } catch (err) {
      console.warn('Failed to load memory data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleDeleteMemory = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this memory?')) return;
    try {
      await memoryService.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      await refreshPendingCounts();
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim() || isSubmitting) return;

    try {
      setIsSubmitting(true);
      const tagsArray = newTags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      await memoryService.createMemory({
        content: newContent.trim(),
        category: newCategory,
        tags: tagsArray,
      });

      setNewContent('');
      setNewTags('');
      setShowAddModal(false);
      fetchData();
    } catch (err: any) {
      alert(`Failed to save memory: ${err.message || 'Error occurred'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const categories: Array<MemoryCategory | 'all'> = [
    'all',
    'personal',
    'project',
    'conversational',
    'knowledge',
  ];

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-3 sm:p-6 custom-scrollbar">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 sm:mb-6 pb-3 sm:pb-4 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-5 h-5 text-emerald-400" />
            <h1 className="text-lg sm:text-xl font-bold text-slate-100">Persistent Personal Memory</h1>
          </div>
          <p className="text-xs text-slate-400">
            Retains preferences, profile facts, and context across sessions with vector retrieval.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded-xl bg-background-tertiary border border-border-subtle text-slate-400 hover:text-slate-100 transition-colors"
            title="Refresh Memories"
            aria-label="Refresh Memories"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Memory</span>
          </button>
        </div>
      </div>

      {/* Pending Consent Suggestions Buffer */}
      {suggestions.length > 0 && (
        <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30">
          <div className="flex items-center gap-2 mb-3 text-emerald-300 font-semibold text-sm">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>Extracted Memory Suggestions Requiring Your Consent ({suggestions.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onRefresh={fetchData}
              />
            ))}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-4">
        {/* Category Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs custom-scrollbar">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-xl capitalize font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-background-secondary text-slate-400 hover:bg-background-tertiary hover:text-slate-200 border border-border-subtle'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Semantic vector search..."
            className="w-full bg-background-secondary border border-border-subtle focus:border-emerald-500/70 rounded-xl py-2 pl-9 pr-3 text-xs text-white placeholder-slate-500 outline-none transition"
          />
        </form>
      </div>

      {/* Memory Cards Grid */}
      <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
        {memories.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            {isLoading ? 'Loading memories...' : 'No memories match your query.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {memories.map((mem) => (
              <div
                key={mem.id}
                className="p-4 rounded-2xl bg-background-secondary border border-border-subtle hover:border-emerald-500/40 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                      {mem.category}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(mem.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed mb-3">
                    {mem.content}
                  </p>

                  {mem.tags && mem.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {mem.tags.map((tag, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-1.5 py-0.5 rounded-md text-[10px] bg-background-tertiary text-slate-400 flex items-center gap-1"
                        >
                          <Tag className="w-2.5 h-2.5" />
                          <span>{tag}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-border-subtle/50 text-[10px] text-slate-500">
                  <span>Source: {mem.source_type}</span>
                  <button
                    onClick={() => handleDeleteMemory(mem.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 transition-opacity"
                    title="Delete Memory"
                    aria-label="Delete Memory"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Memory Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-background-secondary border border-border-subtle rounded-3xl shadow-2xl p-5">
            <h3 className="text-base font-bold text-slate-100 mb-2">Add New Personal Memory</h3>
            <p className="text-xs text-slate-400 mb-4">
              Directly save context, facts, or instructions for LOVE to remember.
            </p>
            <form onSubmit={handleCreateMemory} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Content</label>
                <textarea
                  rows={3}
                  required
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="e.g. I prefer concise markdown output with code blocks"
                  className="w-full p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-xs focus:border-emerald-500 outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                  className="w-full p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-xs focus:border-emerald-500 outline-none"
                >
                  <option value="personal">Personal</option>
                  <option value="project">Project</option>
                  <option value="conversational">Conversational</option>
                  <option value="knowledge">Knowledge</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="e.g. preference, code, markdown"
                  className="w-full p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-xs focus:border-emerald-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-background-tertiary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newContent.trim() || isSubmitting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Save Memory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
