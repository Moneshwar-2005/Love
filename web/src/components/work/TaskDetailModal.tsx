import React, { useState } from 'react';
import { Task } from '../../types/work';
import { workService } from '../../services/workService';
import {
  Ban,
  X,
} from 'lucide-react';

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
  onRefresh: () => void;
}

export const TaskDetailModal: React.FC<TaskDetailModalProps> = ({ task, onClose, onRefresh }) => {
  const [isCancelling, setIsCancelling] = useState(false);
  const [expandedActionId, setExpandedActionId] = useState<string | null>(null);

  const handleCancelTask = async () => {
    try {
      setIsCancelling(true);
      await workService.cancelTask(task.id);
      onRefresh();
    } catch (err) {
      console.error('Failed to cancel task:', err);
    } finally {
      setIsCancelling(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Completed</span>;
      case 'in_progress':
      case 'planning':
      case 'executing':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse">In Progress</span>;
      case 'awaiting_approval':
      case 'waiting_approval':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse">Waiting Approval</span>;
      case 'failed':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">Failed</span>;
      case 'cancelled':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">Cancelled</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-700 text-slate-300">{status}</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-background-secondary border border-border-subtle rounded-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-slate-100">{task.title}</h3>
            {getStatusBadge(task.status)}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-background-tertiary text-slate-400 hover:text-white transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 overflow-y-auto space-y-4 custom-scrollbar text-xs">
          <div>
            <h4 className="font-semibold text-slate-400 mb-1">Description</h4>
            <p className="text-slate-200 bg-background-tertiary/60 p-2.5 rounded-xl border border-border-subtle/50">
              {task.description}
            </p>
          </div>

          {task.result_summary && (
            <div>
              <h4 className="font-semibold text-emerald-400 mb-1">Result Summary</h4>
              <p className="text-slate-200 bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-500/30">
                {task.result_summary}
              </p>
            </div>
          )}

          {task.error_message && (
            <div>
              <h4 className="font-semibold text-rose-400 mb-1">Error Details</h4>
              <p className="text-rose-200 bg-rose-950/20 p-2.5 rounded-xl border border-rose-500/30 font-mono">
                {task.error_message}
              </p>
            </div>
          )}

          {/* Action Step Timeline */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-slate-300">
                Execution Steps ({task.completed_steps} / {task.total_steps || task.actions.length} completed)
              </h4>
            </div>

            <div className="space-y-2">
              {task.actions.map((act) => {
                const isExpanded = expandedActionId === act.id;

                return (
                  <div
                    key={act.id}
                    className="p-3 rounded-xl bg-background-tertiary/50 border border-border-subtle hover:border-border-focus/50 transition-all"
                  >
                    <div
                      className="flex items-center justify-between cursor-pointer"
                      onClick={() => setExpandedActionId(isExpanded ? null : act.id)}
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-[10px] font-mono flex items-center justify-center text-slate-300">
                          {act.step_index + 1}
                        </span>
                        <span className="font-mono text-cyan-400">{act.tool_name}</span>
                        <span className="text-slate-300 truncate max-w-xs">{act.title}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {act.execution_time_ms && (
                          <span className="text-slate-500 font-mono">{act.execution_time_ms}ms</span>
                        )}
                        {getStatusBadge(act.status)}
                      </div>
                    </div>

                    {/* Collapsible Input & Output */}
                    {isExpanded && (
                      <div className="mt-3 pt-3 border-t border-border-subtle/50 space-y-2">
                        <div>
                          <span className="text-slate-400 font-semibold">Input:</span>
                          <pre className="p-2 mt-1 rounded-lg bg-[#090a0f] text-slate-300 font-mono overflow-x-auto text-[11px]">
                            {JSON.stringify(act.input, null, 2)}
                          </pre>
                        </div>

                        {act.output && (
                          <div>
                            <span className="text-slate-400 font-semibold">Output:</span>
                            <pre className="p-2 mt-1 rounded-lg bg-[#090a0f] text-emerald-300 font-mono overflow-x-auto text-[11px]">
                              {JSON.stringify(act.output, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle flex items-center justify-between bg-background-tertiary/30">
          <span className="text-[11px] text-slate-500 font-mono truncate max-w-[180px]">ID: {task.id}</span>
          <div className="flex items-center gap-2">
            {(task.status === 'in_progress' || task.status === 'awaiting_approval') && (
              <button
                onClick={handleCancelTask}
                disabled={isCancelling}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600/20 text-rose-300 hover:bg-rose-600/30 border border-rose-500/40 transition-colors"
              >
                <Ban className="w-3.5 h-3.5" />
                <span>Cancel Task</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
