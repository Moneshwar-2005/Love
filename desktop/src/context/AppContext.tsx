import React, { createContext, useContext, useEffect, useState } from 'react';
import { AssistantState, IntelligenceStatus } from '../types/intelligence';
import { intelligenceService } from '../services/intelligenceService';
import { workService } from '../services/workService';
import { memoryService } from '../services/memoryService';
import { useAuth } from './AuthContext';

export type ActiveView = 'dashboard' | 'chat' | 'work' | 'memory' | 'voice' | 'settings';

interface AppContextType {
  assistantState: AssistantState;
  setAssistantState: (state: AssistantState) => void;
  currentView: ActiveView;
  setCurrentView: (view: ActiveView) => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  intelligenceStatus: IntelligenceStatus | null;
  pendingApprovalsCount: number;
  pendingSuggestionsCount: number;
  backendOnline: boolean;
  refreshStatus: () => Promise<void>;
  refreshPendingCounts: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [currentView, setCurrentView] = useState<ActiveView>('dashboard');
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [intelligenceStatus, setIntelligenceStatus] = useState<IntelligenceStatus | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [pendingSuggestionsCount, setPendingSuggestionsCount] = useState<number>(0);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  const refreshStatus = async () => {
    if (!isAuthenticated) return;
    try {
      const status = await intelligenceService.getStatus();
      setIntelligenceStatus(status);
      setBackendOnline(true);
      if (assistantState === 'offline') {
        setAssistantState('idle');
      }
    } catch {
      setBackendOnline(false);
      setAssistantState('offline');
    }
  };

  const refreshPendingCounts = async () => {
    if (!isAuthenticated) return;
    try {
      const [approvals, suggestions] = await Promise.allSettled([
        workService.listPendingApprovals(),
        memoryService.listSuggestions('pending'),
      ]);

      if (approvals.status === 'fulfilled') {
        setPendingApprovalsCount(approvals.value.length);
        if (approvals.value.length > 0 && assistantState === 'idle') {
          setAssistantState('awaiting_approval');
        } else if (approvals.value.length === 0 && assistantState === 'awaiting_approval') {
          setAssistantState('idle');
        }
      }

      if (suggestions.status === 'fulfilled') {
        setPendingSuggestionsCount(suggestions.value.length);
      }
    } catch (err) {
      console.warn('Failed to refresh pending counts:', err);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      refreshStatus();
      refreshPendingCounts();

      // Periodic light poll for pending counts and backend health (every 15 seconds)
      const timer = setInterval(() => {
        refreshPendingCounts();
      }, 15000);
      return () => clearInterval(timer);
    }
  }, [isAuthenticated]);

  return (
    <AppContext.Provider
      value={{
        assistantState,
        setAssistantState,
        currentView,
        setCurrentView,
        activeConversationId,
        setActiveConversationId,
        intelligenceStatus,
        pendingApprovalsCount,
        pendingSuggestionsCount,
        backendOnline,
        refreshStatus,
        refreshPendingCounts,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
