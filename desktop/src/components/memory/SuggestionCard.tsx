import React, { useState } from 'react';
import { MemorySuggestion } from '../../types/memory';
import { memoryService } from '../../services/memoryService';
import { useApp } from '../../context/AppContext';
import { Check, Sparkles, Tag, X } from 'lucide-react';

interface SuggestionCardProps {
  suggestion: MemorySuggestion;
  onRefresh: () => void;
}

export const SuggestionCard: React.FC<SuggestionCardProps> = ({ suggestion, onRefresh }) => {
  const { refreshPendingCounts } = useApp();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleApprove = async () => {
    try {
      setIsProcessing(true);
      await memoryService.approveSuggestion(suggestion.id);
      await refreshPendingCounts();
      onRefresh();
    } catch (err) {
      console.error('Failed to approve memory suggestion:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    try {
      setIsProcessing(true);
      await memoryService.rejectSuggestion(suggestion.id);
      await refreshPendingCounts();
      onRefresh();
    } catch (err) {
      console.error('Failed to reject memory suggestion:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-3.5 rounded-xl bg-background-secondary border border-emerald-500/30 hover:border-emerald-500/60 transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-xs font-semibold text-emerald-300 capitalize">
              {suggestion.category.replace('_', ' ')}
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {Math.round(suggestion.confidence * 100)}% match
          </span>
        </div>

        <p className="text-xs text-slate-200 mb-2 leading-relaxed">
          "{suggestion.content}"
        </p>

        {suggestion.rationale && (
          <p className="text-[11px] text-slate-400 italic mb-3">
            Reason: {suggestion.rationale}
          </p>
        )}

        {suggestion.tags && suggestion.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {suggestion.tags.map((t, idx) => (
              <span
                key={idx}
                className="px-1.5 py-0.5 rounded text-[10px] bg-background-tertiary text-slate-400 flex items-center gap-1"
              >
                <Tag className="w-2.5 h-2.5" />
                <span>{t}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle/50">
        <button
          onClick={handleReject}
          disabled={isProcessing}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
        >
          <X className="w-3.5 h-3.5" />
          <span>Reject</span>
        </button>

        <button
          onClick={handleApprove}
          disabled={isProcessing}
          className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-600/20 transition-all disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Save Memory</span>
        </button>
      </div>
    </div>
  );
};
