import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { intelligenceService } from '../../services/intelligenceService';
import { Conversation } from '../../types/intelligence';
import {
  Briefcase,
  Database,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Mic,
  Plus,
  Settings,
  Trash2,
  User as UserIcon,
} from 'lucide-react';

interface SidebarProps {
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenSettings }) => {
  const { user, logout } = useAuth();
  const {
    currentView,
    setCurrentView,
    activeConversationId,
    setActiveConversationId,
    pendingApprovalsCount,
    pendingSuggestionsCount,
  } = useApp();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoadingConvs, setIsLoadingConvs] = useState<boolean>(false);

  const fetchConversations = async () => {
    try {
      setIsLoadingConvs(true);
      const list = await intelligenceService.listConversations(30, 0);
      setConversations(list);
      if (list.length > 0 && !activeConversationId) {
        setActiveConversationId(list[0].id);
      }
    } catch (err) {
      console.warn('Failed to fetch conversations:', err);
    } finally {
      setIsLoadingConvs(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleNewChat = async () => {
    try {
      const newConv = await intelligenceService.createConversation('New Conversation');
      setConversations([newConv, ...conversations]);
      setActiveConversationId(newConv.id);
      setCurrentView('chat');
    } catch (err) {
      console.error('Failed to create new chat:', err);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await intelligenceService.deleteConversation(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (activeConversationId === id) {
        setActiveConversationId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  return (
    <aside className="w-64 border-r border-border-subtle bg-background-secondary flex flex-col h-full select-none">
      {/* Primary Navigation Tabs */}
      <div className="p-3 space-y-1">
        <button
          onClick={() => setCurrentView('dashboard')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentView === 'dashboard'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <LayoutDashboard className="w-4 h-4 text-cyan-400" />
            <span>Dashboard</span>
          </div>
        </button>

        <button
          onClick={() => setCurrentView('chat')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentView === 'chat'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <span>Chat</span>
          </div>
        </button>

        <button
          onClick={() => setCurrentView('work')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentView === 'work'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Briefcase className="w-4 h-4 text-amber-400" />
            <span>Work Intelligence</span>
          </div>
          {pendingApprovalsCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-xs font-bold bg-rose-500 text-white">
              {pendingApprovalsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setCurrentView('memory')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentView === 'memory'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-emerald-400" />
            <span>Memory</span>
          </div>
          {pendingSuggestionsCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-xs font-bold bg-emerald-500 text-black">
              {pendingSuggestionsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setCurrentView('voice')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentView === 'voice'
              ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Mic className="w-4 h-4 text-purple-400" />
            <span>Voice Engine</span>
          </div>
        </button>
      </div>

      {/* Conversations Section (when in Chat view) */}
      <div className="flex-1 flex flex-col min-h-0 border-t border-border-subtle pt-3 px-3">
        <div className="flex items-center justify-between mb-2 px-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Conversations
          </span>
          <button
            onClick={handleNewChat}
            className="p-1 rounded-md hover:bg-background-tertiary text-slate-400 hover:text-cyan-400 transition-colors"
            title="Start New Conversation"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-0.5 pr-1 text-sm custom-scrollbar">
          {conversations.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-500">
              No conversations yet
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => {
                  setActiveConversationId(conv.id);
                  setCurrentView('chat');
                }}
                className={`group flex items-center justify-between px-2.5 py-2 rounded-md cursor-pointer transition-colors ${
                  activeConversationId === conv.id && currentView === 'chat'
                    ? 'bg-background-tertiary text-slate-100 font-medium'
                    : 'text-slate-400 hover:bg-background-tertiary/50 hover:text-slate-200'
                }`}
              >
                <span className="truncate text-xs flex-1 mr-2">{conv.title}</span>
                <button
                  onClick={(e) => handleDeleteConversation(e, conv.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-rose-400 transition-opacity"
                  title="Delete Conversation"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Bottom User Profile & Settings */}
      <div className="p-3 border-t border-border-subtle bg-background-tertiary/30 space-y-2">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-background-tertiary transition-colors"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>

        <div className="flex items-center justify-between pt-1 border-t border-border-subtle/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-200">
              {user?.username ? user.username[0].toUpperCase() : <UserIcon className="w-3.5 h-3.5" />}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-slate-200 truncate">
                {user?.full_name || user?.username || 'User'}
              </div>
              <div className="text-[10px] text-cyan-400 font-mono">
                {user?.is_owner ? 'Owner' : 'User'}
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            className="p-1.5 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
