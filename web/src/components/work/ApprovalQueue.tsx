import React, { useState } from 'react';
import { PendingApproval } from '../../types/work';
import { workService } from '../../services/workService';
import { useApp } from '../../context/AppContext';
import { Check, ShieldAlert, X } from 'lucide-react';

interface ApprovalQueueProps {
  approvals: PendingApproval[];
  onRefresh: () => void;
}

export const ApprovalQueue: React.FC<ApprovalQueueProps> = ({ approvals, onRefresh }) => {
  const { refreshPendingCounts } = useApp();
  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleDecision = async (actionId: string, approved: boolean) => {
    try {
      setProcessingId(actionId);
      await workService.resolveApproval(actionId, approved ? 'approve' : 'reject');
      await refreshPendingCounts();
      onRefresh();
    } catch (err) {
      console.error(`Failed to ${approved ? 'approve' : 'reject'} action:`, err);
    } finally {
      setProcessingId(null);
    }
  };

  if (approvals.length === 0) {
    return null;
  }

  return (
    <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30">
      <div className="flex items-center gap-2 mb-3 text-rose-300 font-semibold text-sm">
        <ShieldAlert className="w-5 h-5 text-rose-400" />
        <span>Human-in-the-Loop Authorizations Required ({approvals.length})</span>
      </div>

      <div className="space-y-3">
        {approvals.map(({ task_id, task_title, action }) => {
          const isHighRisk = action.risk_level === 'high' || action.risk_level === 'critical';

          return (
            <div
              key={action.id}
              className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-border-focus transition-all"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-100">{task_title}</span>
                  <span className="text-slate-500 text-xs">/</span>
                  <span className="font-mono text-cyan-400 text-xs">{action.tool_name}</span>
                </div>

                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                    isHighRisk
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  }`}
                >
                  {action.risk_level} risk
                </span>
              </div>

              <p className="text-xs text-slate-300 mb-2">{action.title}</p>

              {/* Tool Parameters Inspection */}
              <div className="p-2.5 rounded-lg bg-[#0b0d14] border border-border-subtle/70 mb-3 text-[11px] font-mono text-slate-300 overflow-x-auto">
                <pre>{JSON.stringify(action.input, null, 2)}</pre>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => handleDecision(action.id, false)}
                  disabled={processingId === action.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-rose-600/30 hover:text-rose-200 border border-border-subtle transition-colors disabled:opacity-50"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </button>

                <button
                  onClick={() => handleDecision(action.id, true)}
                  disabled={processingId === action.id}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Authorize & Run</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
