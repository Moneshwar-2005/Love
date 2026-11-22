import React, { useState } from 'react';
import { ActivityCategory, SystemActivityItem } from '../../types/system';
import {
  Activity,
  Briefcase,
  CheckCircle2,
  Clock,
  Database,
  Laptop,
  MessageSquare,
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

  const filteredItems =
    selectedFilter === 'all'
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
        return 'bg-slate-700 text-slate-300';
    }
  };

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Unified Activity Stream</h3>
            <p className="text-[11px] text-slate-400">Chronological System Events Across Subsystems</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1 overflow-x-auto text-xs custom-scrollbar">
          {(['all', 'intelligence', 'work', 'memory', 'security'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedFilter(cat)}
              className={`px-2 py-0.5 rounded-lg capitalize text-[11px] font-medium transition ${
                selectedFilter === cat
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-2.5 max-h-72 overflow-y-auto custom-scrollbar pr-1">
        {filteredItems.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">
            {isLoading ? 'Loading events...' : 'No activity logged yet.'}
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className="p-3 rounded-xl bg-background-tertiary/50 border border-border-subtle/60 flex items-start justify-between gap-3 text-xs"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="pt-0.5 flex-shrink-0">{getEventIcon(item)}</div>
                <div className="min-w-0">
                  <div className="font-semibold text-slate-200 truncate">{item.title}</div>
                  {item.description && (
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">{item.description}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0 text-[10px]">
                <span
                  className={`px-1.5 py-0.5 rounded border capitalize font-medium ${getCategoryColor(
                    item.category
                  )}`}
                >
                  {item.category}
                </span>
                <span className="text-slate-500 font-mono">
                  {new Date(item.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
