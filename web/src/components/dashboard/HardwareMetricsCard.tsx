import React from 'react';
import { SystemMetrics } from '../../types/system';
import { Cpu, HardDrive, Layers, Server, Zap } from 'lucide-react';

interface HardwareMetricsCardProps {
  metrics: SystemMetrics | null;
  isLoading: boolean;
}

export const HardwareMetricsCard: React.FC<HardwareMetricsCardProps> = ({
  metrics,
  isLoading,
}) => {
  const cpuPercent = metrics ? Math.round(metrics.cpu_percent) : null;
  const ramPercent = metrics ? Math.round(metrics.ram.percent) : null;
  const vramPercent =
    metrics?.gpu.vram_percent !== null && metrics?.gpu.vram_percent !== undefined
      ? Math.round(metrics.gpu.vram_percent)
      : null;
  const gpuUtil =
    metrics?.gpu.utilization_percent !== null && metrics?.gpu.utilization_percent !== undefined
      ? Math.round(metrics.gpu.utilization_percent)
      : null;

  const getProgressColor = (percent: number | null) => {
    if (percent === null) return 'bg-slate-600';
    if (percent > 85) return 'bg-rose-500';
    if (percent > 65) return 'bg-amber-400';
    return 'bg-cyan-500';
  };

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Host Hardware & Resources</h3>
              <p className="text-[11px] text-slate-400">Backend Server Host Telemetry (Distinct from Client)</p>
            </div>
          </div>

          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
            HOST METRICS
          </span>
        </div>

        {/* Real Measurements Grid */}
        <div className="space-y-3.5 mb-4">
          {/* CPU Usage */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>CPU Load</span>
              </span>
              <span className="font-mono text-slate-200 font-semibold">
                {cpuPercent !== null ? `${cpuPercent}%` : 'Unavailable'}
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-background-tertiary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(cpuPercent)}`}
                style={{ width: `${cpuPercent ?? 0}%` }}
              />
            </div>
          </div>

          {/* RAM Usage */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Host RAM</span>
              </span>
              <span className="font-mono text-slate-200 font-semibold">
                {metrics
                  ? `${metrics.ram.used_gb} / ${metrics.ram.total_gb} GB (${ramPercent}%)`
                  : 'Unavailable'}
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-background-tertiary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(ramPercent)}`}
                style={{ width: `${ramPercent ?? 0}%` }}
              />
            </div>
          </div>

          {/* GPU & VRAM */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-400" />
                <span>GPU Acceleration</span>
              </span>
              <span className="font-mono text-slate-200 font-semibold">
                {metrics?.gpu.available ? metrics.gpu.name : 'CPU Fallback'}
              </span>
            </div>
            {metrics?.gpu.available && metrics.gpu.vram_total_gb ? (
              <div className="w-full h-1.5 rounded-full bg-background-tertiary overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getProgressColor(vramPercent)}`}
                  style={{ width: `${vramPercent ?? 0}%` }}
                />
              </div>
            ) : null}
          </div>
        </div>

        {/* Local Model Status */}
        <div className="p-3 rounded-xl bg-background-tertiary/60 border border-border-subtle/70 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-300">
              Ollama Daemon: {metrics?.local_model.is_running ? 'Online' : 'Standby / Stopped'}
            </span>
          </div>
          {metrics?.local_model.latency_ms && (
            <span className="text-slate-400 font-mono text-[11px]">
              {metrics.local_model.latency_ms}ms ping
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
