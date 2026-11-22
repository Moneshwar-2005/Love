import React, { useState } from 'react';
import { ActivityCategory, SystemActivityItem } from '../../types/system';
import {
  Activity,
  Briefcase,
  CheckCircle2,
  Clock,
  Database,
  Filter,
  Laptop,
  MessageSquare,
  Mic,
  Shield,
  XCircle,
} from 'lucide-react';

interface ActivityTimelineProps {
  items: SystemActivityItem[];
  isLoading: boolean;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  items,
  isLoading,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<ActivityCategory | 'all'>('all');

  const filteredItems = selectedFilter === 'all'
    ? items
    : items.filter((item) => item.category === selectedFilter);

  const getEventIcon = (item: SystemActivityItem) => {
    switch (item.event_type) {
      case 'conversation_created':
        return <MessageSquare className="w-3.5 h-3.5 text-cyan-400" />;
      case 'task_created':
        return <Briefcase className="w-3.5 h-3.5 text-amber-400" />;
      case 'task_completed':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'task_failed':
      case 'action_rejected':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
      case 'action_awaiting_approval':
      case 'action_approved':
        return <Briefcase className="w-3.5 h-3.5 text-purple-400" />;
      case 'memory_saved':
        return <Database className="w-3.5 h-3.5 text-emerald-400" />;
      case 'device_registered':
        return <Laptop className="w-3.5 h-3.5 text-blue-400" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getCategoryColor = (cat: ActivityCategory) => {
    switch (cat) {
      case 'intelligence':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'work':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'memory':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'voice':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'security':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md">
      {/* Header with Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Unified Activity Timeline</h3>
            <p className="text-[11px] text-slate-400">Chronological System Events Across Domains</p>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 text-xs overflow-x-auto pb-1">
          {(['all', 'intelligence', 'work', 'memory', 'security'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedFilter(cat)}
              className={`px-2 py-1 rounded-lg capitalize font-medium text-[11px] transition-colors whitespace-nowrap ${
                selectedFilter === cat
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-background-tertiary/70 text-slate-400 hover:text-slate-200 border border-border-subtle'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Stream */}
      <div className="space-y-2 max-h-72 overflow-y-auto custom-scrollbar pr-1">
        {filteredItems.length === 0 ? (
          <div className="text-center py-10 text-xs text-slate-500">
            {isLoading ? 'Loading system activity...' : 'No activity recorded in this category'}
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className="p-3 rounded-xl bg-background-tertiary/40 border border-border-subtle hover:border-border-subtle/90 transition-all flex items-start justify-between gap-3 group"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="p-1.5 rounded-lg bg-background-secondary border border-border-subtle flex-shrink-0 mt-0.5">
                  {getEventIcon(item)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-semibold text-slate-100">
                      {item.title}
                    </span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-semibold border capitalize ${getCategoryColor(item.category)}`}>
                      {item.category}
                    </span>
                  </div>
                  {item.description && (
                    <p className="text-[11px] text-slate-400 leading-relaxed truncate">
                      {item.description}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono whitespace-nowrap flex-shrink-0 mt-1">
                <Clock className="w-3 h-3 text-slate-600" />
                <span>{formatTimestamp(item.timestamp)}</span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="pt-3 border-t border-border-subtle/60 mt-3 flex items-center justify-between text-[10px] text-slate-500">
        <span>Genuine Events Only (Non-Fabricated)</span>
        <span>Showing {filteredItems.length} of {items.length} Recorded</span>
      </div>
    </div>
  );
};
