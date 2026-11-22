import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppProvider, useApp } from './context/AppContext';
import { AuthScreen } from './components/auth/AuthScreen';
import { AppLayout } from './components/layout/AppLayout';
import { ChatWorkspace } from './components/chat/ChatWorkspace';
import { WorkWorkspace } from './components/work/WorkWorkspace';
import { MemoryWorkspace } from './components/memory/MemoryWorkspace';
import { CommandDashboard } from './components/dashboard/CommandDashboard';
import { VoiceWorkspace } from './components/voice/VoiceWorkspace';
import { SettingsModal } from './components/settings/SettingsModal';
import { SystemStatusModal } from './components/status/SystemStatusModal';
import { Bot } from 'lucide-react';

const MainApplication: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { currentView, setCurrentView } = useApp();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isStatusOpen, setIsStatusOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-[#090a0f] flex flex-col items-center justify-center select-none text-slate-300">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white mb-4 shadow-xl shadow-cyan-600/30 animate-pulse">
          <Bot className="w-7 h-7" />
        </div>
        <div className="text-sm font-semibold tracking-wide text-slate-200">Initializing LOVE Workspace...</div>
        <div className="text-xs text-slate-500 mt-1">Verifying secure browser session</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  return (
    <AppLayout
      onOpenSystemStatus={() => setIsStatusOpen(true)}
      onOpenSettings={() => setIsSettingsOpen(true)}
    >
      {currentView === 'dashboard' && (
        <CommandDashboard
          onNavigate={(view) => setCurrentView(view)}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />
      )}

      {currentView === 'chat' && <ChatWorkspace />}

      {currentView === 'work' && <WorkWorkspace />}

      {currentView === 'memory' && <MemoryWorkspace />}

      {currentView === 'voice' && <VoiceWorkspace />}

      {/* Modals */}
      {isSettingsOpen && (
        <SettingsModal onClose={() => setIsSettingsOpen(false)} />
      )}

      {isStatusOpen && (
        <SystemStatusModal onClose={() => setIsStatusOpen(false)} />
      )}
    </AppLayout>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppProvider>
        <MainApplication />
      </AppProvider>
    </AuthProvider>
  );
};

export default App;
