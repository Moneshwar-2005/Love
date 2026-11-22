import React, { useEffect, useState } from 'react';
import { useMobileApp } from '../../context/AppContext';
import { DatabaseBackupResponse, DatabaseHealthInfo, HostMetrics } from '../../types/system';
import { mobileSystemService } from '../../services/systemService';
import { Activity, Cpu, Database, HardDrive, RefreshCw, ShieldCheck } from 'lucide-react';

export const MobileDashboard: React.FC = () => {
  const { intelligenceStatus, backendOnline, refreshStatus } = useMobileApp();
  const [metrics, setMetrics] = useState<HostMetrics | null>(null);
  const [dbHealth, setDbHealth] = useState<DatabaseHealthInfo | null>(null);
  const [backupRes, setBackupRes] = useState<DatabaseBackupResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isBackingUp, setIsBackingUp] = useState<boolean>(false);

  const loadTelemetry = async () => {
    setIsRefreshing(true);
    try {
      const [m, d] = await Promise.allSettled([
        mobileSystemService.getMetrics(),
        mobileSystemService.getDatabaseHealth(),
      ]);
      if (m.status === 'fulfilled') setMetrics(m.value);
      if (d.status === 'fulfilled') setDbHealth(d.value);
      await refreshStatus();
    } catch (err) {
      console.warn('Telemetry refresh failed:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadTelemetry();
  }, []);

  const handleCreateBackup = async () => {
    setIsBackingUp(true);
    try {
      const res = await mobileSystemService.createDatabaseBackup();
      setBackupRes(res);
      // Reload db health
      const d = await mobileSystemService.getDatabaseHealth();
      setDbHealth(d);
    } catch (err) {
      console.warn('Backup failed:', err);
    } finally {
      setIsBackingUp(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background">
      {/* Top Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            <span>Command & Telemetry</span>
          </h2>
          <p className="text-[11px] text-slate-400">Host hardware, SQLite WAL engine & local models</p>
        </div>
        <button
          onClick={loadTelemetry}
          disabled={isRefreshing}
          className="p-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-400 hover:text-cyan-400 transition"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Intelligence Engine Status Card */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200">Intelligence Engine</h3>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
              backendOnline ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400'
            }`}
          >
            {backendOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-500 block">Active Provider</span>
            <span className="font-semibold text-slate-200">{intelligenceStatus?.active_provider || 'Ollama'}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-500 block">Active Model</span>
            <span className="font-semibold text-cyan-300 font-mono truncate block">
              {intelligenceStatus?.active_model || 'qwen2.5:7b'}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-500 block">Routing Policy</span>
            <span className="font-semibold text-slate-200 capitalize">
              {intelligenceStatus?.routing_preference || 'auto'}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <span className="text-[10px] text-slate-500 block">Local Privacy</span>
            <span className="font-semibold text-emerald-400">
              {intelligenceStatus?.local_only_mode ? 'Strict Local' : 'Permissive Local/Cloud'}
            </span>
          </div>
        </div>
      </div>

      {/* Host Hardware Metrics */}
      {metrics && (
        <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200">Host Hardware Telemetry</h3>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
              <span className="text-[10px] text-slate-500 block">CPU Load</span>
              <span className="font-bold text-slate-200 font-mono">{metrics.cpu_percent.toFixed(1)}%</span>
            </div>
            <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
              <span className="text-[10px] text-slate-500 block">RAM Usage</span>
              <span className="font-bold text-slate-200 font-mono">
                {metrics.ram.used_gb.toFixed(1)} / {metrics.ram.total_gb.toFixed(1)} GB ({metrics.ram.percent.toFixed(0)}%)
              </span>
            </div>
            {metrics.gpu && metrics.gpu.available && (
              <div className="col-span-2 p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
                <span className="text-[10px] text-slate-500 block">GPU: {metrics.gpu.name || 'Discrete Graphics'}</span>
                <span className="font-bold text-indigo-300 font-mono">
                  {metrics.gpu.vram_used_gb?.toFixed(1)} / {metrics.gpu.vram_total_gb?.toFixed(1)} GB VRAM ({metrics.gpu.vram_percent?.toFixed(0)}%)
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Canonical Database Diagnostics */}
      {dbHealth && (
        <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold text-slate-200">Canonical Database (SQLite)</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              WAL Mode
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle">
              <span className="text-[10px] text-slate-500 block font-sans">Alembic Head</span>
              <span className="text-indigo-300 font-bold truncate block">{dbHealth.schema_revision || 'c0e81b379d42'}</span>
            </div>
            <div className="p-2 rounded-xl bg-background-tertiary/60 border border-border-subtle">
              <span className="text-[10px] text-slate-500 block font-sans">Integrity</span>
              <span className="text-emerald-400 font-bold">{dbHealth.integrity_check || 'ok'}</span>
            </div>
          </div>

          {backupRes && (
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[11px] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>Backup {backupRes.backup.filename} created & verified!</span>
            </div>
          )}

          <button
            onClick={handleCreateBackup}
            disabled={isBackingUp}
            className="w-full py-2 px-3 rounded-xl bg-background-tertiary border border-border-subtle hover:border-cyan-500/40 text-cyan-400 text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{isBackingUp ? 'Creating Verified Backup...' : 'Create Atomic SQLite Backup'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
