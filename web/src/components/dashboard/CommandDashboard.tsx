import React, { useCallback, useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { intelligenceService } from '../../services/intelligenceService';
import { memoryService } from '../../services/memoryService';
import { systemService } from '../../services/systemService';
import { syncService } from '../../services/syncService';
import { workService } from '../../services/workService';
import { MemoryStats } from '../../types/memory';
import { DatabaseHealthInfo, SystemActivityItem, SystemMetrics } from '../../types/system';
import { SyncStatus } from '../../types/sync';
import { ActivityTimeline } from './ActivityTimeline';
import { DatabaseHealthCard } from './DatabaseHealthCard';
import { HardwareMetricsCard } from './HardwareMetricsCard';
import {
  AlertTriangle,
  Briefcase,
  Database,
  Gauge,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

interface CommandDashboardProps {
  onNavigate: (view: 'dashboard' | 'chat' | 'work' | 'memory' | 'voice' | 'settings') => void;
  onOpenSettings: () => void;
}

export const CommandDashboard: React.FC<CommandDashboardProps> = ({
  onNavigate,
  onOpenSettings,
}) => {
  const {
    intelligenceStatus,
    pendingApprovalsCount,
    pendingSuggestionsCount,
    refreshStatus,
    refreshPendingCounts,
  } = useApp();

  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [dbHealth, setDbHealth] = useState<DatabaseHealthInfo | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [activity, setActivity] = useState<SystemActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [metricsRes, dbHealthRes, syncRes, memStatsRes, actRes] =
        await Promise.allSettled([
          systemService.getMetrics(),
          systemService.getDatabaseHealth(),
          syncService.getStatus(),
          memoryService.getStats(),
          systemService.getActivity(20),
        ]);

      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value);
      if (dbHealthRes.status === 'fulfilled') setDbHealth(dbHealthRes.value);
      if (syncRes.status === 'fulfilled') setSyncStatus(syncRes.value);
      if (memStatsRes.status === 'fulfilled') setMemoryStats(memStatsRes.value);
      if (actRes.status === 'fulfilled') setActivity(actRes.value.items || []);

      await refreshStatus();
      await refreshPendingCounts();
    } catch (err) {
      console.warn('Dashboard data fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [refreshStatus, refreshPendingCounts]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto p-3 sm:p-6 custom-scrollbar space-y-5">
      {/* Dashboard Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg sm:text-xl font-bold text-slate-100">Command & Observability Dashboard</h1>
          </div>
          <p className="text-xs text-slate-400">
            Real-time telemetry, model routing, database health, and system activity.
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-300 hover:text-white text-xs font-medium transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Quick Status KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Intelligence Model Card */}
        <div
          onClick={() => onNavigate('chat')}
          className="p-4 rounded-2xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 cursor-pointer transition-all flex flex-col justify-between group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-medium">Active Intelligence</span>
            <Sparkles className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-sm font-bold text-slate-100 truncate">
            {intelligenceStatus?.active_provider || 'Ollama'} • {intelligenceStatus?.active_model || 'auto'}
          </div>
          <div className="text-[10px] text-cyan-400 mt-2 font-mono flex items-center gap-1">
            <span>Routing: {intelligenceStatus?.routing_preference || 'auto'}</span>
          </div>
        </div>

        {/* Work Approvals Card */}
        <div
          onClick={() => onNavigate('work')}
          className="p-4 rounded-2xl bg-background-secondary border border-border-subtle hover:border-amber-500/50 cursor-pointer transition-all flex flex-col justify-between group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-medium">Pending Approvals</span>
            <AlertTriangle className={`w-4 h-4 ${pendingApprovalsCount > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-500'}`} />
          </div>
          <div className="text-sm font-bold text-slate-100">
            {pendingApprovalsCount} Authorizations
          </div>
          <div className="text-[10px] text-amber-400 mt-2 font-mono">
            {pendingApprovalsCount > 0 ? 'Action required in Work' : 'All tool actions authorized'}
          </div>
        </div>

        {/* Memory Stats Card */}
        <div
          onClick={() => onNavigate('memory')}
          className="p-4 rounded-2xl bg-background-secondary border border-border-subtle hover:border-emerald-500/50 cursor-pointer transition-all flex flex-col justify-between group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-medium">Personal Memories</span>
            <Database className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-sm font-bold text-slate-100">
            {memoryStats?.total_memories ?? 0} Memories ({pendingSuggestionsCount} Suggestions)
          </div>
          <div className="text-[10px] text-emerald-400 mt-2 font-mono">
            Vector Dimension: {memoryStats?.embedding_dimension ?? 128}d
          </div>
        </div>

        {/* Sync & Device Security Card */}
        <div
          onClick={onOpenSettings}
          className="p-4 rounded-2xl bg-background-secondary border border-border-subtle hover:border-indigo-500/50 cursor-pointer transition-all flex flex-col justify-between group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-medium">Sync & Security</span>
            <ShieldCheck className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-sm font-bold text-slate-100 capitalize">
            {syncStatus?.sync_mode || 'Standalone'}
          </div>
          <div className="text-[10px] text-indigo-300 mt-2 font-mono">
            Cursor: #{syncStatus?.current_cursor ?? 0} • Events: {syncStatus?.total_events ?? 0}
          </div>
        </div>
      </div>

      {/* Database Health Card & Host Hardware Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DatabaseHealthCard
          dbHealth={dbHealth}
          isLoading={isLoading}
          onRefresh={fetchDashboardData}
        />
        <HardwareMetricsCard
          metrics={metrics}
          isLoading={isLoading}
        />
      </div>

      {/* Activity Timeline */}
      <ActivityTimeline
        items={activity}
        isLoading={isLoading}
      />
    </div>
  );
};
