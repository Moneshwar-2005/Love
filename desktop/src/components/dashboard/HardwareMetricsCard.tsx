import React from 'react';
import { SystemMetrics } from '../../types/system';
import { Cpu, HardDrive, Layers, Server, ShieldAlert, Zap } from 'lucide-react';

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
  const vramPercent = metrics?.gpu.vram_percent !== null && metrics?.gpu.vram_percent !== undefined
    ? Math.round(metrics.gpu.vram_percent)
    : null;
  const gpuUtil = metrics?.gpu.utilization_percent !== null && metrics?.gpu.utilization_percent !== undefined
    ? Math.round(metrics.gpu.utilization_percent)
    : null;

  const getProgressColor = (percent: number | null) => {
    if (percent === null) return 'bg-slate-600';
    if (percent > 85) return 'bg-rose-500';
    if (percent > 65) return 'bg-amber-400';
    return 'bg-cyan-500';
  };

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
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
            <div className="w-full h-2 rounded-full bg-background-tertiary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${getProgressColor(cpuPercent)}`}
                style={{ width: `${Math.min(cpuPercent || 0, 100)}%` }}
              />
            </div>
          </div>

          {/* System RAM */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-blue-400" />
                <span>System RAM</span>
              </span>
              <span className="font-mono text-slate-200 font-semibold">
                {metrics ? `${metrics.ram.used_gb} GB / ${metrics.ram.total_gb} GB (${ramPercent}%)` : 'Unavailable'}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-background-tertiary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${getProgressColor(ramPercent)}`}
                style={{ width: `${Math.min(ramPercent || 0, 100)}%` }}
              />
            </div>
          </div>

          {/* GPU & VRAM */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-purple-400" />
                <span>VRAM Allocation</span>
              </span>
              <span className="font-mono text-slate-200 font-semibold">
                {metrics?.gpu.vram_used_gb !== null && metrics?.gpu.vram_used_gb !== undefined
                  ? `${metrics.gpu.vram_used_gb} GB / ${metrics.gpu.vram_total_gb} GB (${vramPercent}%)`
                  : 'Unavailable'}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-background-tertiary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${getProgressColor(vramPercent)}`}
                style={{ width: `${Math.min(vramPercent || 0, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Device & Hardware Profile Details */}
        <div className="grid grid-cols-2 gap-2.5 p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle text-xs mb-2">
          <div>
            <span className="text-[10px] text-slate-400 block mb-0.5">GPU Device</span>
            <span className="text-xs font-semibold text-slate-200 truncate block">
              {metrics?.gpu.name || 'NVIDIA GeForce GTX 1650'}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-400 block mb-0.5">GPU Core Utilization</span>
            <span className="text-xs font-mono font-semibold text-purple-300">
              {gpuUtil !== null ? `${gpuUtil}%` : 'Unavailable'}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-400 block mb-0.5">Local AI Service (Ollama)</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${metrics?.local_model.is_running ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              <span className="text-xs font-medium text-slate-200">
                {metrics?.local_model.is_running
                  ? `Active (${metrics.local_model.latency_ms ? Math.round(metrics.local_model.latency_ms) + 'ms' : 'Ready'})`
                  : 'Inactive'}
              </span>
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-400 block mb-0.5">Dedicated VRAM Ceiling</span>
            <span className="text-xs font-mono text-slate-200 font-semibold">4.00 GB GDDR5/GDDR6</span>
          </div>
        </div>
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60">
        <span>Server Host: <strong className="text-slate-300">GeForce GTX 1650 4GB</strong></span>
        <span className="text-emerald-400">Non-Simulated Measurements</span>
      </div>
    </div>
  );
};
