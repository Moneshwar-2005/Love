import React from 'react';
import { Task } from '../../types/work';
import { AlertTriangle, ArrowUpRight, Briefcase, CheckCircle2, Clock, Play, ShieldAlert, XCircle } from 'lucide-react';

interface WorkActivityCardProps {
  tasks: Task[];
  pendingApprovalsCount: number;
  onNavigateToWork: () => void;
}

export const WorkActivityCard: React.FC<WorkActivityCardProps> = ({
  tasks,
  pendingApprovalsCount,
  onNavigateToWork,
}) => {
  const inProgress = tasks.filter((t) => t.status === 'in_progress').length;
  const completed = tasks.filter((t) => t.status === 'completed').length;
  const failed = tasks.filter((t) => t.status === 'failed').length;
  const awaitingApproval = tasks.filter((t) => t.status === 'awaiting_approval').length;
  const cancelled = tasks.filter((t) => t.status === 'cancelled').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-400">Completed</span>;
      case 'in_progress':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/15 text-cyan-400 animate-pulse">Running</span>;
      case 'awaiting_approval':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-400">Awaiting Auth</span>;
      case 'failed':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-300">Failed</span>;
      case 'cancelled':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-500/15 text-slate-400">Cancelled</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-500/15 text-slate-400 capitalize">{status}</span>;
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Briefcase className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Work & Task Orchestration</h3>
              <p className="text-[11px] text-slate-400">Safe Tools & Supervised Autonomous Work</p>
            </div>
          </div>

          <button
            onClick={onNavigateToWork}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 transition-all group"
          >
            <span>Open Work</span>
            <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>

        {/* Pending Approvals Critical Banner */}
        {pendingApprovalsCount > 0 && (
          <div className="mb-3.5 p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 flex items-center justify-between gap-3 animate-pulse">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-rose-200">
                  {pendingApprovalsCount} Action Authorization{pendingApprovalsCount > 1 ? 's' : ''} Pending
                </div>
                <div className="text-[10px] text-rose-300/80">
                  High-risk tools paused waiting for user approval.
                </div>
              </div>
            </div>
            <button
              onClick={onNavigateToWork}
              className="px-3 py-1 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-600/30 transition-all"
            >
              Review Queue
            </button>
          </div>
        )}

        {/* Tasks Breakdown Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-4">
          <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Running</span>
            <div className="text-sm font-bold text-cyan-400">{inProgress}</div>
          </div>

          <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Completed</span>
            <div className="text-sm font-bold text-emerald-400">{completed}</div>
          </div>

          <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Awaiting</span>
            <div className="text-sm font-bold text-rose-400">{awaitingApproval}</div>
          </div>

          <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Failed</span>
            <div className="text-sm font-bold text-rose-300">{failed}</div>
          </div>

          <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center col-span-2 sm:col-span-1">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">Cancelled</span>
            <div className="text-sm font-bold text-slate-400">{cancelled}</div>
          </div>
        </div>

        {/* Recent Tasks List */}
        <div className="space-y-1.5">
          <span className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider block px-1">
            Recent Work Tasks
          </span>
          <div className="space-y-1.5 max-h-36 overflow-y-auto custom-scrollbar pr-1">
            {tasks.length === 0 ? (
              <div className="p-3 rounded-xl bg-background-tertiary text-center text-xs text-slate-500">
                No work tasks executed yet
              </div>
            ) : (
              tasks.slice(0, 3).map((t) => (
                <div
                  key={t.id}
                  onClick={onNavigateToWork}
                  className="p-2.5 rounded-xl bg-background-tertiary/40 border border-border-subtle hover:border-amber-500/30 cursor-pointer transition-colors flex items-center justify-between gap-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      {getStatusBadge(t.status)}
                      <span className="text-[10px] text-slate-500 font-mono">
                        Steps: {t.completed_steps}/{t.total_steps}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-slate-200 truncate">{t.title}</p>
                  </div>
                  <span className="text-[10px] text-slate-500 whitespace-nowrap">
                    {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60 mt-2">
        <span>Total Tracked Tasks: <strong className="text-slate-200">{tasks.length}</strong></span>
        <span className="text-amber-400 font-semibold">Zero Auto-Approvals</span>
      </div>
    </div>
  );
};
