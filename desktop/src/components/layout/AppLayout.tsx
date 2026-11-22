import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { AuthScreen } from '../auth/AuthScreen';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { ChatWorkspace } from '../chat/ChatWorkspace';
import { WorkWorkspace } from '../work/WorkWorkspace';
import { MemoryWorkspace } from '../memory/MemoryWorkspace';
import { VoiceWorkspace } from '../voice/VoiceWorkspace';
import { CommandDashboard } from '../dashboard/CommandDashboard';
import { SystemStatusModal } from '../status/SystemStatusModal';
import { SettingsModal } from '../settings/SettingsModal';

export const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { currentView, setCurrentView } = useApp();
  const [showSystemStatus, setShowSystemStatus] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-[#090a0f] flex items-center justify-center text-cyan-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-400">Initializing LOVE Desktop...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  return (
    <div className="h-screen w-full bg-[#090a0f] flex flex-col overflow-hidden text-slate-100">
      {/* Top Header */}
      <Header onOpenSystemStatus={() => setShowSystemStatus(true)} />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <Sidebar onOpenSettings={() => setShowSettings(true)} />

        {/* Dynamic Content View Area */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {currentView === 'dashboard' && (
            <CommandDashboard
              onNavigate={(v) => setCurrentView(v)}
              onOpenSettings={() => setShowSettings(true)}
            />
          )}
          {currentView === 'chat' && <ChatWorkspace />}
          {currentView === 'work' && <WorkWorkspace />}
          {currentView === 'memory' && <MemoryWorkspace />}
          {currentView === 'voice' && <VoiceWorkspace />}
        </main>
      </div>

      {/* Overlays / Modals */}
      {showSystemStatus && (
        <SystemStatusModal onClose={() => setShowSystemStatus(false)} />
      )}

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
};
