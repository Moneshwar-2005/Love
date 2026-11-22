import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { intelligenceService } from '../../services/intelligenceService';
import { memoryService } from '../../services/memoryService';
import { systemService, DeviceInfo } from '../../services/systemService';
import { voiceService } from '../../services/voiceService';
import { workService } from '../../services/workService';
import { ProviderStatus } from '../../types/intelligence';
import { Memory, MemoryStats } from '../../types/memory';
import { DatabaseHealthInfo, SystemActivityItem, SystemMetrics } from '../../types/system';
import { VoiceStatus } from '../../types/voice';
import { Task } from '../../types/work';
import { ActivityTimeline } from './ActivityTimeline';
import { DatabaseHealthCard } from './DatabaseHealthCard';
import { HardwareMetricsCard } from './HardwareMetricsCard';
import { IdentityStateCard } from './IdentityStateCard';
import { IntelligenceCard } from './IntelligenceCard';
import { MemorySummaryCard } from './MemorySummaryCard';
import { SecurityDeviceCard } from './SecurityDeviceCard';
import { VoiceStatusCard } from './VoiceStatusCard';
import { WorkActivityCard } from './WorkActivityCard';
import { AlertCircle, Gauge, RefreshCw } from 'lucide-react';

interface CommandDashboardProps {
  onNavigate: (view: 'dashboard' | 'chat' | 'work' | 'memory' | 'voice' | 'settings') => void;
  onOpenSettings?: () => void;
}

export const CommandDashboard: React.FC<CommandDashboardProps> = ({
  onNavigate,
  onOpenSettings,
}) => {
  const { refreshStatus, refreshPendingCounts } = useApp();

  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [recentMemories, setRecentMemories] = useState<Memory[]>([]);
  const [pendingSuggestionsCount, setPendingSuggestionsCount] = useState<number>(0);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [dbHealth, setDbHealth] = useState<DatabaseHealthInfo | null>(null);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [activity, setActivity] = useState<SystemActivityItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  const isMountedRef = useRef<boolean>(true);

  const fetchDashboardData = useCallback(async (isBackground: boolean = false) => {
    if (!isBackground) {
      setIsRefreshing(true);
    }

    try {
      const [
        metricsRes,
        providersRes,
        memStatsRes,
        memoriesRes,
        suggestionsRes,
        tasksRes,
        approvalsRes,
        voiceRes,
        dbHealthRes,
        devicesRes,
        activityRes,
      ] = await Promise.allSettled([
        systemService.getMetrics(),
        intelligenceService.listProviders(),
        memoryService.getStats(),
        memoryService.listMemories({ limit: 5 }),
        memoryService.listSuggestions('pending'),
        workService.listTasks(undefined, 20),
        workService.listPendingApprovals(),
        voiceService.getStatus(),
        systemService.getDatabaseHealth(),
        systemService.listDevices(),
        systemService.getActivity(25),
      ]);

      if (!isMountedRef.current) return;

      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value);
      if (providersRes.status === 'fulfilled') setProviders(providersRes.value);
      if (memStatsRes.status === 'fulfilled') setMemoryStats(memStatsRes.value);
      if (memoriesRes.status === 'fulfilled') setRecentMemories(memoriesRes.value);
      if (suggestionsRes.status === 'fulfilled') setPendingSuggestionsCount(suggestionsRes.value.length);
      if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value);
      if (approvalsRes.status === 'fulfilled') setPendingApprovalsCount(approvalsRes.value.length);
      if (voiceRes.status === 'fulfilled') setVoiceStatus(voiceRes.value);
      if (dbHealthRes.status === 'fulfilled') setDbHealth(dbHealthRes.value);
      if (devicesRes.status === 'fulfilled') setDevices(devicesRes.value.devices || []);
      if (activityRes.status === 'fulfilled') setActivity(activityRes.value.items || []);

      setLastUpdated(new Date());
      setErrorNotice(null);

      // Also trigger global app context updates
      refreshStatus().catch(() => {});
      refreshPendingCounts().catch(() => {});
    } catch (err: any) {
      if (isMountedRef.current) {
        setErrorNotice(err.message || 'Failed to refresh dashboard data.');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [refreshStatus, refreshPendingCounts]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchDashboardData(false);

    // Controlled polling timer every 25 seconds
    const intervalId = setInterval(() => {
      fetchDashboardData(true);
    }, 25000);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [fetchDashboardData]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-4 sm:p-6 custom-scrollbar overflow-y-auto">
      {/* Top Banner & Title Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 shadow-lg shadow-cyan-500/20 text-white">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-100">Command Dashboard</h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/25">
                LIVE TELEMETRY
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Real-time operational observability of LOVE intelligence, memory, tools, voice, and system health.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => fetchDashboardData(false)}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/40 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Metrics'}</span>
          </button>
        </div>
      </div>

      {/* Error Alert if any */}
      {errorNotice && (
        <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-2.5 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{errorNotice}</span>
        </div>
      )}

      {/* Section 1: Top Hero Grid (Identity & Hardware) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <IdentityStateCard
          lastUpdated={lastUpdated}
          isLoading={isRefreshing}
          onRefresh={() => fetchDashboardData(false)}
          uptimeSeconds={metrics?.uptime_seconds || 0}
          onNavigate={(view) => onNavigate(view)}
        />
        <HardwareMetricsCard
          metrics={metrics}
          isLoading={isLoading}
        />
      </div>

      {/* Section 2: Core Subsystems Grid (Intelligence, Memory, Work, Voice) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-4">
        <IntelligenceCard
          providers={providers}
          totalModels={providers.reduce((acc, p) => acc + (p.models_count || 0), 0)}
          onNavigateToChat={() => onNavigate('chat')}
        />
        <MemorySummaryCard
          stats={memoryStats}
          pendingSuggestionsCount={pendingSuggestionsCount}
          recentMemories={recentMemories}
          onNavigateToMemory={() => onNavigate('memory')}
        />
        <WorkActivityCard
          tasks={tasks}
          pendingApprovalsCount={pendingApprovalsCount}
          onNavigateToWork={() => onNavigate('work')}
        />
        <VoiceStatusCard
          status={voiceStatus}
          onNavigateToVoice={() => onNavigate('voice')}
        />
      </div>

      {/* Section 3: Database & Security Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <DatabaseHealthCard
          dbHealth={dbHealth}
          isLoading={isLoading}
          onRefresh={() => fetchDashboardData(true)}
        />
        <SecurityDeviceCard
          devices={devices}
          onOpenSettings={() => onOpenSettings ? onOpenSettings() : onNavigate('settings')}
        />
      </div>

      {/* Section 4: Activity Timeline */}
      <div className="mb-4">
        <ActivityTimeline
          items={activity}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};
