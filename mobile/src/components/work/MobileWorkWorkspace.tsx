import React, { useEffect, useState } from 'react';
import { useMobileApp } from '../../context/AppContext';
import { PendingApproval, Task } from '../../types/work';
import { mobileWorkService } from '../../services/workService';
import { AlertTriangle, Check, CheckSquare, Plus, RefreshCw, X } from 'lucide-react';

export const MobileWorkWorkspace: React.FC = () => {
  const { pendingApprovalsCount, refreshCounts } = useMobileApp();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'tasks' | 'approvals'>('approvals');
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newTaskTitle, setNewTaskTitle] = useState<string>('');
  const [newTaskDesc, setNewTaskDesc] = useState<string>('');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [tList, aList] = await Promise.allSettled([
        mobileWorkService.listTasks(),
        mobileWorkService.listPendingApprovals(),
      ]);
      if (tList.status === 'fulfilled') setTasks(tList.value);
      if (aList.status === 'fulfilled') setApprovals(aList.value);
      await refreshCounts();
    } catch (err) {
      console.warn('Failed to load work data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleResolveApproval = async (actionId: string, approved: boolean) => {
    try {
      await mobileWorkService.resolveApproval(actionId, approved);
      setApprovals((prev) => prev.filter((a) => a.action.id !== actionId));
      await refreshCounts();
      await loadData();
    } catch (err) {
      console.warn('Resolve approval error:', err);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    try {
      await mobileWorkService.createTask({
        title: newTaskTitle.trim(),
        description: newTaskDesc.trim(),
        auto_execute: true,
      });
      setShowCreateModal(false);
      setNewTaskTitle('');
      setNewTaskDesc('');
      await loadData();
      setActiveTab('tasks');
    } catch (err) {
      console.warn('Create task error:', err);
    }
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'medium':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background">
      {/* Work Sub-Header & Segmented Control */}
      <div className="flex items-center justify-between">
        <div className="flex bg-background-secondary p-1 rounded-xl border border-border-subtle">
          <button
            onClick={() => setActiveTab('approvals')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === 'approvals'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Approvals</span>
            {pendingApprovalsCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] font-bold ${
                activeTab === 'approvals' ? 'bg-slate-950 text-cyan-400' : 'bg-rose-500 text-white'
              }`}>
                {pendingApprovalsCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              activeTab === 'tasks'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Tasks ({tasks.length})
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            aria-label="Create task"
            className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 transition"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={loadData}
            disabled={isLoading}
            aria-label="Refresh"
            className="p-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-400 hover:text-cyan-400 transition"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* APPROVALS TAB */}
      {activeTab === 'approvals' && (
        <div className="space-y-3">
          {approvals.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <CheckSquare className="w-10 h-10 text-emerald-400/50 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-300">No Pending Approvals</h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                All autonomous work actions have been authorized or completed.
              </p>
            </div>
          ) : (
            approvals.map((item) => (
              <div
                key={item.action.id}
                className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                      Task: {item.task_title}
                    </span>
                    <h4 className="text-xs font-bold text-white mt-0.5">{item.action.title}</h4>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border font-mono ${getRiskBadge(
                      item.action.risk_level
                    )}`}
                  >
                    {item.action.risk_level}
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-background-tertiary/70 border border-border-subtle text-[11px] font-mono text-slate-300 space-y-1">
                  <div>
                    <span className="text-slate-500">Tool: </span>
                    <span className="text-cyan-300">{item.action.tool_name}</span>
                  </div>
                  {item.action.input && (
                    <div className="truncate text-slate-400">
                      Input: {JSON.stringify(item.action.input)}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => handleResolveApproval(item.action.id, false)}
                    className="flex-1 py-2 rounded-xl bg-background-tertiary border border-border-subtle hover:bg-rose-500/20 text-rose-400 font-semibold text-xs flex items-center justify-center gap-1.5 transition"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                  <button
                    onClick={() => handleResolveApproval(item.action.id, true)}
                    className="flex-1 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition shadow-lg shadow-cyan-500/20"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Authorize</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TASKS TAB */}
      {activeTab === 'tasks' && (
        <div className="space-y-3">
          {tasks.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <CheckSquare className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-300">No Work Tasks</h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Create an autonomous work task to execute complex plans with human verification.
              </p>
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-2 cursor-pointer hover:border-cyan-500/30 transition"
              >
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white truncate max-w-[70%]">{task.title}</h4>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold capitalize bg-background-tertiary text-slate-300 border border-border-subtle">
                    {task.status}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">{task.description}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 font-mono">
                  <span>
                    Steps: {task.completed_steps || 0} / {task.total_steps || task.plan?.length || 0}
                  </span>
                  <span>{new Date(task.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Task Plan Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-background-secondary border border-border-subtle rounded-3xl p-5 space-y-4 max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div>
                <h3 className="text-sm font-bold text-white">{selectedTask.title}</h3>
                <span className="text-[10px] font-mono text-cyan-400 capitalize">{selectedTask.status}</span>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              <p className="text-xs text-slate-300">{selectedTask.description}</p>

              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Execution Plan</h4>
              {selectedTask.plan && selectedTask.plan.length > 0 ? (
                selectedTask.plan.map((step, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-[11px] space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">Step {step.step || idx + 1}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono ${getRiskBadge(step.risk_level)}`}>
                        {step.risk_level}
                      </span>
                    </div>
                    <p className="text-slate-400">{step.description}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500">No explicit plan steps recorded.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-background-secondary border border-border-subtle rounded-3xl p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h3 className="text-sm font-bold text-white">Create Work Task</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Task Title</label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="e.g. Audit workspace security"
                  required
                  className="w-full px-3 py-2 rounded-xl bg-background-tertiary border border-border-subtle text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Goal & Description</label>
                <textarea
                  rows={3}
                  value={newTaskDesc}
                  onChange={(e) => setNewTaskDesc(e.target.value)}
                  placeholder="Describe the desired outcome..."
                  required
                  className="w-full px-3 py-2 rounded-xl bg-background-tertiary border border-border-subtle text-xs text-slate-100 focus:outline-none focus:border-cyan-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="py-2 px-3 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="py-2 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition"
                >
                  Plan & Launch Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
