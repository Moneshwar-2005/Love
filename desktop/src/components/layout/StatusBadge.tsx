import React from 'react';
import { AssistantState } from '../../types/intelligence';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Mic,
  Volume2,
  WifiOff,
  Zap,
} from 'lucide-react';

interface StatusBadgeProps {
  state: AssistantState;
  className?: string;
  showText?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  state,
  className = '',
  showText = true,
}) => {
  const getBadgeConfig = () => {
    switch (state) {
      case 'idle':
        return {
          label: 'Ready',
          color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          dot: 'bg-emerald-400',
          icon: CheckCircle2,
          pulse: false,
        };
      case 'thinking':
        return {
          label: 'Thinking...',
          color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          dot: 'bg-cyan-400',
          icon: Zap,
          pulse: true,
        };
      case 'responding':
        return {
          label: 'Generating',
          color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
          dot: 'bg-indigo-400',
          icon: Activity,
          pulse: true,
        };
      case 'listening':
        return {
          label: 'Listening',
          color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          dot: 'bg-amber-400',
          icon: Mic,
          pulse: true,
        };
      case 'speaking':
        return {
          label: 'Speaking',
          color: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
          dot: 'bg-purple-400',
          icon: Volume2,
          pulse: true,
        };
      case 'awaiting_approval':
        return {
          label: 'Awaiting Approval',
          color: 'bg-rose-500/15 text-rose-400 border-rose-500/40',
          dot: 'bg-rose-400',
          icon: AlertTriangle,
          pulse: true,
        };
      case 'offline':
      default:
        return {
          label: 'Backend Offline',
          color: 'bg-slate-800 text-slate-400 border-slate-700',
          dot: 'bg-slate-500',
          icon: WifiOff,
          pulse: false,
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm transition-all duration-300 ${config.color} ${className}`}
      data-testid="status-badge"
    >
      <span className="relative flex h-2 w-2">
        {config.pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.dot}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dot}`} />
      </span>
      <Icon className="w-3.5 h-3.5 opacity-80" />
      {showText && <span>{config.label}</span>}
    </div>
  );
};
