import React, { useEffect, useState } from 'react';
import { useApp, ActiveView } from '../../context/AppContext';
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
  Search,
  Settings,
  Trash2,
  X,
} from 'lucide-react';

interface SidebarProps {
  onOpenSettings: () => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenSettings,
  isOpenMobile = false,
  onCloseMobile,
}) => {
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
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoadingConvs, setIsLoadingConvs] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchConversations = async () => {
    try {
      setIsLoadingConvs(true);
      const list = await intelligenceService.listConversations(50, 0);
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
      if (onCloseMobile) onCloseMobile();
    } catch (err) {
      console.error('Failed to create new conversation:', err);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this conversation? This will delete all messages.')) {
      return;
    }
    try {
      setDeletingId(id);
      await intelligenceService.deleteConversation(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (activeConversationId === id) {
        setActiveConversationId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const navItems: Array<{
    id: ActiveView;
    label: string;
    icon: React.ElementType;
    badge?: number;
    badgeColor?: string;
  }> = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'Assistant Chat', icon: MessageSquare },
    {
      id: 'work',
      label: 'Work Intelligence',
      icon: Briefcase,
      badge: pendingApprovalsCount,
      badgeColor: 'bg-rose-500 text-white',
    },
    {
      id: 'memory',
      label: 'Personal Memory',
      icon: Database,
      badge: pendingSuggestionsCount,
      badgeColor: 'bg-cyan-500 text-black',
    },
    { id: 'voice', label: 'Voice Engine', icon: Mic },
  ];

  const sidebarContent = (
    <aside className="w-64 h-full bg-background-secondary border-r border-border-subtle flex flex-col select-none">
      {/* Mobile Close Bar */}
      <div className="flex md:hidden items-center justify-between p-3 border-b border-border-subtle">
        <span className="text-xs font-semibold text-slate-300">Navigation Menu</span>
        <button
          type="button"
          onClick={onCloseMobile}
          className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-background-tertiary"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Primary Navigation Views */}
      <div className="p-3 border-b border-border-subtle space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                setCurrentView(item.id);
                if (onCloseMobile) onCloseMobile();
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-300 hover:bg-background-tertiary hover:text-white'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && item.badge > 0 ? (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                    item.badgeColor || 'bg-slate-700 text-slate-200'
                  }`}
                >
                  {item.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {/* Conversation Thread History (Collapsible / Dynamic) */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="p-3 pb-2 flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-400 tracking-wider uppercase">
            Conversations
          </span>
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1 text-[11px] font-medium text-cyan-400 hover:text-cyan-300 transition px-2 py-0.5 rounded-md hover:bg-cyan-500/10"
            title="Start New Conversation"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter threads..."
              className="w-full bg-background border border-border-subtle focus:border-cyan-500/60 rounded-lg py-1.5 pl-8 pr-2.5 text-xs text-white placeholder-slate-600 outline-none transition"
            />
          </div>
        </div>

        {/* List of Conversations */}
        <div className="flex-1 overflow-y-auto px-2 space-y-0.5 custom-scrollbar">
          {isLoadingConvs && conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500">Loading threads...</div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500">
              {searchQuery ? 'No matching threads' : 'No conversations yet'}
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isSelected = activeConversationId === c.id;
              return (
                <div
                  key={c.id}
                  onClick={() => {
                    setActiveConversationId(c.id);
                    setCurrentView('chat');
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`group relative flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition ${
                    isSelected
                      ? 'bg-background-tertiary text-cyan-300 font-medium border border-border-subtle'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-background-tertiary/50'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
                    <span className="truncate">{c.title || 'Untitled'}</span>
                  </div>

                  <button
                    onClick={(e) => handleDeleteConversation(e, c.id)}
                    disabled={deletingId === c.id}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 rounded transition"
                    title="Delete Conversation"
                    aria-label={`Delete conversation ${c.title}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer Settings & User Info */}
      <div className="p-3 border-t border-border-subtle bg-background-secondary/50">
        <button
          onClick={() => {
            onOpenSettings();
            if (onCloseMobile) onCloseMobile();
          }}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-background-tertiary transition"
        >
          <Settings className="w-4 h-4" />
          <span>Sync & System Settings</span>
        </button>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:block h-full">{sidebarContent}</div>

      {/* Mobile Drawer with Backdrop */}
      {isOpenMobile && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 h-full">{sidebarContent}</div>
        </div>
      )}
    </>
  );
};
