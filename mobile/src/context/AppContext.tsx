/**
 * LOVE Mobile Application Context.
 * Manages active navigation tabs, assistant conversational state, and pending HITL approval/consent badges.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { AssistantState, IntelligenceStatus } from '../types/intelligence';
import { mobileIntelligenceService } from '../services/intelligenceService';
import { mobileMemoryService } from '../services/memoryService';
import { mobileWorkService } from '../services/workService';
import { useMobileAuth } from './AuthContext';

export type MobileTab = 'chat' | 'dashboard' | 'work' | 'memory' | 'settings';

interface MobileAppContextType {
  activeTab: MobileTab;
  setActiveTab: (tab: MobileTab) => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  assistantState: AssistantState;
  setAssistantState: (state: AssistantState) => void;
  intelligenceStatus: IntelligenceStatus | null;
  backendOnline: boolean;
  pendingApprovalsCount: number;
  pendingSuggestionsCount: number;
  refreshCounts: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

const MobileAppContext = createContext<MobileAppContextType | undefined>(undefined);

export const MobileAppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useMobileAuth();
  const [activeTab, setActiveTab] = useState<MobileTab>('chat');
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [intelligenceStatus, setIntelligenceStatus] = useState<IntelligenceStatus | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [pendingSuggestionsCount, setPendingSuggestionsCount] = useState<number>(0);

  const refreshStatus = async () => {
    if (!isAuthenticated) return;
    try {
      const status = await mobileIntelligenceService.getStatus();
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

  const refreshCounts = async () => {
    if (!isAuthenticated) return;
    try {
      const [approvals, suggestions] = await Promise.allSettled([
        mobileWorkService.listPendingApprovals(),
        mobileMemoryService.listSuggestions('pending'),
      ]);

      if (approvals.status === 'fulfilled') {
        setPendingApprovalsCount(approvals.value.length);
      }
      if (suggestions.status === 'fulfilled') {
        setPendingSuggestionsCount(suggestions.value.length);
      }
    } catch {
      // Non-blocking
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      refreshStatus();
      refreshCounts();
    }
  }, [isAuthenticated]);

  return (
    <MobileAppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        activeConversationId,
        setActiveConversationId,
        assistantState,
        setAssistantState,
        intelligenceStatus,
        backendOnline,
        pendingApprovalsCount,
        pendingSuggestionsCount,
        refreshCounts,
        refreshStatus,
      }}
    >
      {children}
    </MobileAppContext.Provider>
  );
};

export const useMobileApp = (): MobileAppContextType => {
  const context = useContext(MobileAppContext);
  if (!context) {
    throw new Error('useMobileApp must be used within a MobileAppProvider');
  }
  return context;
};
