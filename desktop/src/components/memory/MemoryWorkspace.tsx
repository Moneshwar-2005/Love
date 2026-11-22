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
          ? memoryService.searchMemories({
              query: searchQuery.trim(),
              category: selectedCategory === 'all' ? undefined : selectedCategory,
              limit: 50,
            })
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
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-6 custom-scrollbar">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-slate-100">Persistent Personal Memory</h1>
          </div>
          <p className="text-xs text-slate-400">
            Retains preferences, profile facts, and context across sessions with vector retrieval.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded-lg bg-background-tertiary border border-border-subtle text-slate-400 hover:text-slate-100 transition-colors"
            title="Refresh Memories"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Memory</span>
          </button>
        </div>
      </div>

      {/* Pending Consent / Approval Suggestions */}
      {suggestions.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              Discovered Suggestions Awaiting Your Consent ({suggestions.length})
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {suggestions.map((sug) => (
              <SuggestionCard key={sug.id} suggestion={sug} onRefresh={fetchData} />
            ))}
          </div>
        </div>
      )}

      {/* Search Bar & Category Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memories semantically or by keywords..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-background-secondary border border-border-subtle focus:border-emerald-500 text-xs text-slate-100 placeholder-slate-500 outline-none"
          />
        </form>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1.5 rounded-lg capitalize font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-background-secondary text-slate-400 hover:bg-background-tertiary hover:text-slate-200 border border-border-subtle'
              }`}
            >
              {cat.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Memories List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar pr-1">
        {memories.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            {isLoading ? 'Loading memories...' : 'No memories found.'}
          </div>
        ) : (
          memories.map((mem) => (
            <div
              key={mem.id}
              className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-emerald-500/40 transition-all flex items-start justify-between gap-3 group"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                    {mem.category.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {new Date(mem.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed mb-2">
                  {mem.content}
                </p>
                {mem.tags && mem.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {mem.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded text-[10px] bg-background-tertiary text-slate-400 flex items-center gap-0.5"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        <span>{tag}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <button
                onClick={() => handleDeleteMemory(mem.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-rose-500/10 hover:text-rose-400 text-slate-500 transition-all"
                title="Delete Memory"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Add Memory Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-background-secondary border border-border-subtle rounded-2xl shadow-2xl p-5">
            <h3 className="text-base font-bold text-slate-100 mb-2">Store Permanent Memory</h3>
            <p className="text-xs text-slate-400 mb-4">
              Add explicit knowledge or personal preferences directly into LOVE's persistent memory.
            </p>
            <form onSubmit={handleCreateMemory} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Content</label>
                <textarea
                  rows={3}
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="e.g. My primary coding language is Python and I prefer concise explanations."
                  className="w-full p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-xs focus:border-emerald-500 outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                  className="w-full p-2 rounded-xl bg-background-tertiary border border-border-subtle text-slate-200 text-xs focus:border-emerald-500 outline-none capitalize"
                >
                  <option value="personal">Personal</option>
                  <option value="project">Project</option>
                  <option value="conversational">Conversational</option>
                  <option value="knowledge">Knowledge</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="coding, python, style"
                  className="w-full p-2 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-xs focus:border-emerald-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:bg-background-tertiary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newContent.trim() || isSubmitting}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all disabled:opacity-50"
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
