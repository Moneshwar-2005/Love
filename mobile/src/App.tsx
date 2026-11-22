import React, { useEffect } from 'react';
import { MobileAuthProvider, useMobileAuth } from './context/AuthContext';
import { MobileAppProvider, useMobileApp } from './context/AppContext';
import { MobileHeader } from './components/layout/MobileHeader';
import { MobileTabBar } from './components/layout/MobileTabBar';
import { SafeAreaContainer } from './components/layout/SafeAreaContainer';
import { MobileAuthScreen } from './components/auth/MobileAuthScreen';
import { MobileChatWorkspace } from './components/chat/MobileChatWorkspace';
import { MobileDashboard } from './components/dashboard/MobileDashboard';
import { MobileWorkWorkspace } from './components/work/MobileWorkWorkspace';
import { MobileMemoryWorkspace } from './components/memory/MobileMemoryWorkspace';
import { MobileSettingsScreen } from './components/settings/MobileSettingsScreen';
import { mobileNativeDeviceService } from './services/nativeDeviceService';

const MainAppContent: React.FC = () => {
  const { isAuthenticated, isLoading } = useMobileAuth();
  const { activeTab } = useMobileApp();

  useEffect(() => {
    mobileNativeDeviceService.initializeNativeFeatures();
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-background text-cyan-400 space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center font-bold text-xl animate-pulse">
          L
        </div>
        <p className="text-xs text-slate-400 font-mono tracking-wider">Starting LOVE Mobile...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <SafeAreaContainer topOnly bottomOnly>
        <MobileAuthScreen />
      </SafeAreaContainer>
    );
  }

  const getTitle = () => {
    switch (activeTab) {
      case 'chat':
        return 'Assistant Dialogue';
      case 'work':
        return 'Work Intelligence';
      case 'memory':
        return 'Personal Memory';
      case 'dashboard':
        return 'Telemetry & Diagnostics';
      case 'settings':
        return 'Mobile Settings';
      default:
        return 'LOVE';
    }
  };

  return (
    <SafeAreaContainer>
      <MobileHeader title={getTitle()} />
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {activeTab === 'chat' && <MobileChatWorkspace />}
        {activeTab === 'work' && <MobileWorkWorkspace />}
        {activeTab === 'memory' && <MobileMemoryWorkspace />}
        {activeTab === 'dashboard' && <MobileDashboard />}
        {activeTab === 'settings' && <MobileSettingsScreen />}
      </main>
      <MobileTabBar />
    </SafeAreaContainer>
  );
};

export const App: React.FC = () => {
  return (
    <MobileAuthProvider>
      <MobileAppProvider>
        <MainAppContent />
      </MobileAppProvider>
    </MobileAuthProvider>
  );
};

export default App;
