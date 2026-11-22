import React, { useEffect, useState } from 'react';
import { Conversation } from '../../types/intelligence';
import { mobileIntelligenceService } from '../../services/intelligenceService';
import { MessageSquare, Plus, Trash2, X } from 'lucide-react';

interface MobileConversationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
}

export const MobileConversationDrawer: React.FC<MobileConversationDrawerProps> = ({
  isOpen,
  onClose,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const list = await mobileIntelligenceService.listConversations();
      setConversations(list);
    } catch (err) {
      console.warn('Failed to load conversations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await mobileIntelligenceService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        onNewConversation();
      }
    } catch (err) {
      console.warn('Failed to delete conversation:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div onClick={onClose} className="fixed inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Drawer */}
      <div className="relative w-4/5 max-w-xs bg-background-secondary h-full border-r border-border-subtle flex flex-col z-10 shadow-2xl">
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <span>Conversations</span>
          </h2>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="p-1 rounded-lg text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={() => {
              onNewConversation();
              onClose();
            }}
            className="w-full py-2 px-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-semibold text-xs flex items-center justify-center gap-2 hover:bg-cyan-500/20 transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-3 space-y-1 py-1">
          {isLoading ? (
            <div className="text-center py-8 text-xs text-slate-500">Loading dialogue history...</div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">No active conversations</div>
          ) : (
            conversations.map((c) => {
              const isSelected = c.id === activeConversationId;
              return (
                <div
                  key={c.id}
                  onClick={() => {
                    onSelectConversation(c.id);
                    onClose();
                  }}
                  className={`p-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer transition ${
                    isSelected
                      ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-300 hover:bg-background-tertiary border border-transparent'
                  }`}
                >
                  <span className="truncate pr-2 font-medium">{c.title || 'Untitled Dialogue'}</span>
                  <button
                    onClick={(e) => handleDelete(e, c.id)}
                    aria-label="Delete conversation"
                    className="p-1 text-slate-500 hover:text-rose-400 transition shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
