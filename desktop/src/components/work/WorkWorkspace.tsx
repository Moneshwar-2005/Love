import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { workService } from '../../services/workService';
import { PendingApproval, Task, TaskStatus } from '../../types/work';
import { ApprovalQueue } from './ApprovalQueue';
import { TaskDetailModal } from './TaskDetailModal';
import {
  Briefcase,
  CheckCircle2,
  Filter,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react';

export const WorkWorkspace: React.FC = () => {
  const { pendingApprovalsCount, refreshPendingCounts } = useApp();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showNewTaskModal, setShowNewTaskModal] = useState<boolean>(false);
  const [newTaskInput, setNewTaskInput] = useState<string>('');
  const [isSubmittingTask, setIsSubmittingTask] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [fetchedApprovals, fetchedTasks] = await Promise.all([
        workService.listPendingApprovals(),
        workService.listTasks(statusFilter === 'all' ? undefined : statusFilter, 50, 0),
      ]);
      setApprovals(fetchedApprovals);
      setTasks(fetchedTasks);
    } catch (err) {
      console.warn('Failed to fetch work tasks or approvals:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskInput.trim() || isSubmittingTask) return;

    try {
      setIsSubmittingTask(true);
      await workService.createTask({
        description: newTaskInput.trim(),
        auto_execute: true,
      });
      setNewTaskInput('');
      setShowNewTaskModal(false);
      await refreshPendingCounts();
      fetchData();
    } catch (err) {
      console.error('Failed to create task:', err);
    } finally {
      setIsSubmittingTask(false);
    }
  };

  const getStatusBadge = (status: TaskStatus) => {
    switch (status) {
      case 'completed':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Completed</span>;
      case 'in_progress':
      case 'planning':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse">In Progress</span>;
      case 'awaiting_approval':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse">Needs Approval</span>;
      case 'failed':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">Failed</span>;
      case 'cancelled':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">Cancelled</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-700 text-slate-300">{status}</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-6 custom-scrollbar">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Briefcase className="w-5 h-5 text-amber-400" />
            <h1 className="text-xl font-bold text-slate-100">Universal Work Intelligence</h1>
          </div>
          <p className="text-xs text-slate-400">
            Automated task planning, safe tool execution, and Human-in-the-Loop authorization.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded-lg bg-background-tertiary border border-border-subtle text-slate-400 hover:text-slate-100 transition-colors"
            title="Refresh Tasks"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowNewTaskModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-600/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Task</span>
          </button>
        </div>
      </div>

      {/* Pending Approvals Section (Sticky Alert at top) */}
      <ApprovalQueue approvals={approvals} onRefresh={fetchData} />

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1 text-xs">
        {(['all', 'in_progress', 'awaiting_approval', 'completed', 'failed', 'cancelled'] as const).map(
          (filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`px-3 py-1.5 rounded-lg capitalize font-medium transition-colors ${
                statusFilter === filter
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-background-secondary text-slate-400 hover:bg-background-tertiary hover:text-slate-200 border border-border-subtle'
              }`}
            >
              {filter.replace('_', ' ')}
            </button>
          )
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-1">
        {tasks.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            {isLoading ? 'Loading tasks...' : 'No tasks match current filter.'}
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              onClick={() => setSelectedTask(task)}
              className="p-4 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 cursor-pointer transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 group"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2.5 mb-1.5">
                  <h3 className="font-semibold text-slate-200 text-sm truncate group-hover:text-cyan-300 transition-colors">
                    {task.title}
                  </h3>
                  {getStatusBadge(task.status)}
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 mb-2">
                  {task.description}
                </p>
                <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono">
                  <span>Steps: {task.completed_steps} / {task.total_steps || task.actions.length}</span>
                  <span>Created: {new Date(task.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center">
                <span className="text-xs font-semibold text-cyan-400 group-hover:translate-x-1 transition-transform">
                  Inspect &rarr;
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onRefresh={fetchData}
        />
      )}

      {/* New Task Modal */}
      {showNewTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-background-secondary border border-border-subtle rounded-2xl shadow-2xl p-5">
            <h3 className="text-base font-bold text-slate-100 mb-2">Create Work Intelligence Task</h3>
            <p className="text-xs text-slate-400 mb-4">
              Describe the objective you want LOVE to accomplish using registered tools.
            </p>
            <form onSubmit={handleCreateTask}>
              <textarea
                rows={4}
                value={newTaskInput}
                onChange={(e) => setNewTaskInput(e.target.value)}
                placeholder="e.g. Calculate 18% of 45000 and write a summary to the workspace"
                className="w-full p-3 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 text-sm focus:border-cyan-500 outline-none resize-none mb-4"
              />
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowNewTaskModal(false)}
                  className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-400 hover:bg-background-tertiary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newTaskInput.trim() || isSubmittingTask}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-600/25 transition-all disabled:opacity-50"
                >
                  {isSubmittingTask ? 'Planning & Running...' : 'Execute Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
