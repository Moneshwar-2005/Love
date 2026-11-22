import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface AppLayoutProps {
  children: React.ReactNode;
  onOpenSystemStatus: () => void;
  onOpenSettings: () => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  onOpenSystemStatus,
  onOpenSettings,
}) => {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="flex flex-col h-screen w-screen bg-background text-slate-100 overflow-hidden">
      <Header
        onOpenSystemStatus={onOpenSystemStatus}
        onOpenSettings={onOpenSettings}
        onToggleMobileNav={() => setIsMobileNavOpen(!isMobileNavOpen)}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          onOpenSettings={onOpenSettings}
          isOpenMobile={isMobileNavOpen}
          onCloseMobile={() => setIsMobileNavOpen(false)}
        />

        <main className="flex-1 flex flex-col min-w-0 bg-background overflow-hidden relative">
          {children}
        </main>
      </div>
    </div>
  );
};
