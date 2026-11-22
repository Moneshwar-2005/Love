import React from 'react';
import { useMobileApp, MobileTab } from '../../context/AppContext';
import { Activity, Brain, CheckSquare, MessageSquare, Settings } from 'lucide-react';

export const MobileTabBar: React.FC = () => {
  const { activeTab, setActiveTab, pendingApprovalsCount, pendingSuggestionsCount } = useMobileApp();

  const tabs: Array<{ id: MobileTab; label: string; icon: React.FC<{ className?: string }>; badge?: number }> = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'work', label: 'Work', icon: CheckSquare, badge: pendingApprovalsCount },
    { id: 'memory', label: 'Memory', icon: Brain, badge: pendingSuggestionsCount },
    { id: 'dashboard', label: 'Telemetry', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <nav className="h-16 bg-background-secondary/95 backdrop-blur-lg border-t border-border-subtle flex items-center justify-around px-2 z-30 shrink-0">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            data-tab={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex flex-col items-center justify-center flex-1 h-full py-1 transition-colors ${
              isActive ? 'text-cyan-400 font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className="relative">
              <Icon className={`w-5 h-5 ${isActive ? 'scale-110 text-cyan-400' : ''} transition-transform`} />
              {typeof tab.badge === 'number' && tab.badge > 0 && (
                <span className="absolute -top-1.5 -right-2 px-1.5 py-0.2 bg-rose-500 text-white font-mono text-[9px] font-bold rounded-full border border-background">
                  {tab.badge > 99 ? '99+' : tab.badge}
                </span>
              )}
            </div>
            <span className="text-[10px] mt-1 tracking-tight">{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
